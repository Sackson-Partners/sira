/**
 * SIRA Mobile — Image Preprocessor
 * ==================================
 * Resize and compress images **before** they are uploaded to the backend or
 * sent to any AI API.  This prevents the Anthropic error:
 *   "image dimensions exceed max allowed size: 2000 pixels"
 *
 * Backend applies a second resize pass (max 1568px) as a safety net, but
 * reducing on-device first dramatically cuts upload bandwidth.
 *
 * Requires:  expo-image-manipulator  (~12.x, Expo SDK 51)
 *
 * Usage:
 *   import { preprocessImageForUpload } from '../utils/imagePreprocessor';
 *
 *   const result = await preprocessImageForUpload(pickerAsset.uri);
 *   // result.uri  — local path to the resized/compressed file
 *   // result.width / result.height
 *
 * For batches:
 *   const results = await preprocessImagesForUpload(assets.map(a => a.uri));
 */

import * as ImageManipulator from 'expo-image-manipulator';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Max width or height sent from the mobile client. */
const MAX_MOBILE_DIMENSION = 1200;

/** JPEG quality (0–1).  0.7 balances size vs. quality for evidence photos. */
const JPEG_COMPRESS_QUALITY = 0.7;

/** Hard server-side cap.  We never send anything larger. */
const HARD_MAX_DIMENSION = 2000;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PreprocessedImage {
  uri: string;
  width: number;
  height: number;
  /** Original URI before processing */
  originalUri: string;
  /** Whether the image was actually resized */
  wasResized: boolean;
  /** Original dimensions */
  originalWidth?: number;
  originalHeight?: number;
}

export interface PreprocessOptions {
  /** Max dimension in pixels (default 1200) */
  maxDimension?: number;
  /** JPEG compress quality 0–1 (default 0.7) */
  quality?: number;
}

// ---------------------------------------------------------------------------
// Core preprocessing
// ---------------------------------------------------------------------------

/**
 * Resize and compress a single image URI.
 *
 * - If max(width, height) > maxDimension → resize proportionally
 * - Always saves as JPEG at `quality` compression
 * - Rejects (throws) if image still exceeds HARD_MAX_DIMENSION after processing
 *
 * @param uri   Local file URI (from expo-image-picker or expo-camera)
 * @param opts  Optional overrides for maxDimension and quality
 */
export async function preprocessImageForUpload(
  uri: string,
  opts: PreprocessOptions = {},
): Promise<PreprocessedImage> {
  const maxDimension = opts.maxDimension ?? MAX_MOBILE_DIMENSION;
  const quality = opts.quality ?? JPEG_COMPRESS_QUALITY;

  // Get original dimensions by opening the image with no transforms first.
  const probe = await ImageManipulator.manipulateAsync(uri, [], {
    format: ImageManipulator.SaveFormat.JPEG,
  });
  const origW = probe.width;
  const origH = probe.height;

  console.log(
    `[ImagePreprocessor] Original: ${origW}x${origH} — URI: ${uri.slice(-40)}`,
  );

  // Determine whether a resize is needed.
  const largest = Math.max(origW, origH);
  const needsResize = largest > maxDimension;

  const transforms: ImageManipulator.Action[] = [];
  if (needsResize) {
    // Maintain aspect ratio by only specifying the constrained axis.
    if (origW >= origH) {
      transforms.push({ resize: { width: maxDimension } });
    } else {
      transforms.push({ resize: { height: maxDimension } });
    }
  }

  const result = await ImageManipulator.manipulateAsync(uri, transforms, {
    compress: quality,
    format: ImageManipulator.SaveFormat.JPEG,
  });

  console.log(
    `[ImagePreprocessor] Result: ${result.width}x${result.height} ` +
      `(resized=${needsResize}, quality=${quality})`,
  );

  // Safety guard — should never trigger with correct maxDimension logic.
  if (Math.max(result.width, result.height) > HARD_MAX_DIMENSION) {
    throw new Error(
      `Image ${result.width}x${result.height} still exceeds the ` +
        `${HARD_MAX_DIMENSION}px hard limit after preprocessing. ` +
        `Cannot upload this image.`,
    );
  }

  return {
    uri: result.uri,
    width: result.width,
    height: result.height,
    originalUri: uri,
    wasResized: needsResize,
    originalWidth: origW,
    originalHeight: origH,
  };
}

/**
 * Preprocess a batch of image URIs.
 *
 * @param uris      Array of local file URIs
 * @param opts      Shared options applied to every image
 * @param onError   Called for each failed image; if omitted the error is thrown
 */
export async function preprocessImagesForUpload(
  uris: string[],
  opts: PreprocessOptions = {},
  onError?: (uri: string, error: Error) => void,
): Promise<PreprocessedImage[]> {
  const results: PreprocessedImage[] = [];

  for (const uri of uris) {
    try {
      const processed = await preprocessImageForUpload(uri, opts);
      results.push(processed);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      console.warn(`[ImagePreprocessor] Failed to process ${uri}: ${error.message}`);
      if (onError) {
        onError(uri, error);
      } else {
        throw error;
      }
    }
  }

  console.log(
    `[ImagePreprocessor] Batch complete: ${results.length}/${uris.length} images processed.`,
  );
  return results;
}

// ---------------------------------------------------------------------------
// FormData helper
// ---------------------------------------------------------------------------

/**
 * Build a FormData object with a preprocessed image ready for multipart upload.
 *
 * Example:
 *   const form = await buildImageFormData(uri, 'file', { filename: 'evidence.jpg' });
 *   await apiClient.post('/evidences/upload/42', form, {
 *     headers: { 'Content-Type': 'multipart/form-data' },
 *   });
 */
export async function buildImageFormData(
  uri: string,
  fieldName: string = 'file',
  extra: { filename?: string; mimeType?: string } = {},
  opts: PreprocessOptions = {},
): Promise<FormData> {
  const processed = await preprocessImageForUpload(uri, opts);

  const form = new FormData();
  // React Native FormData accepts an object with uri/name/type for file fields.
  form.append(fieldName, {
    uri: processed.uri,
    name: extra.filename ?? 'evidence.jpg',
    type: extra.mimeType ?? 'image/jpeg',
  } as unknown as Blob);

  return form;
}
