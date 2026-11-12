"""Offline, color-managed losses between an Image grade and a rendered global LUT."""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageOps
from scipy.ndimage import gaussian_filter, gaussian_gradient_magnitude

# Keep working-space normalization and Oklab conversion in sync with the LUT renderer.
from color_match_lut import read_srgb, to_oklab

LOSS_KEYS = ("rgb_l1", "delta_e00", "luma_dssim", "oklab_swd")
_SRGB_TO_XYZ = np.array([
    [.4124564, .3575761, .1804375],
    [.2126729, .7151522, .0721750],
    [.0193339, .1191920, .9503041],
])
_D65_WHITE = np.array([.95047, 1., 1.08883])
_LUMA = np.array([.2126, .7152, .0722])


def _load_image(source, max_edge):
    if isinstance(source, (str, Path)):
        image, info = read_srgb(source, long_edge=max_edge)
        return image, tuple(info["source_size"])

    if not isinstance(source, Image.Image):
        raise TypeError("Expected an image path or Pillow image")
    if source.mode in {"I", "F", "I;16", "I;16B", "I;16L"}:
        raise ValueError("Convert 16-bit or HDR images to SDR sRGB before measuring")
    profile = source.info.get("icc_profile")
    image = ImageOps.exif_transpose(source)
    size = image.size
    image = _downsample(image, max_edge)
    alpha = image.getchannel("A") if "A" in image.getbands() else None
    if profile:
        image = ImageCms.profileToProfile(
            image.convert("RGB") if alpha is not None else image,
            ImageCms.ImageCmsProfile(io.BytesIO(profile)),
            ImageCms.createProfile("sRGB"),
            outputMode="RGB",
        )
    else:
        image = image.convert("RGB")
    if alpha is not None:
        background = Image.new("RGB", image.size, "white")
        background.paste(image, mask=alpha)
        image = background
    return image, size


def _downsample(image, max_edge):
    factor = min(1., max_edge / max(image.size))
    if factor == 1.:
        return image
    size = tuple(max(1, round(dimension * factor)) for dimension in image.size)
    return image.resize(size, Image.Resampling.LANCZOS)


def _pair(first, second, max_edge):
    if max_edge < 1:
        raise ValueError("max_edge must be positive")
    first, first_size = _load_image(first, max_edge)
    second, second_size = _load_image(second, max_edge)
    # Never increase sampling resolution beyond the smaller native long side.
    edge = min(max_edge, max(first_size), max(second_size))
    first = _downsample(first, edge)
    if second.size != first.size:
        second = second.resize(first.size, Image.Resampling.LANCZOS)
    return (
        np.asarray(first, dtype=np.float64) / 255.,
        np.asarray(second, dtype=np.float64) / 255.,
        first_size,
        second_size,
    )


def screen_geometry(source, reference, *, max_edge=768, max_aspect_error=.02, min_edge_correlation=.80):
    """Flag non-global spatial differences before ranking a grading reference."""
    first, second, source_size, reference_size = _pair(source, reference, max_edge)
    aspect_error = abs((reference_size[0] / reference_size[1]) / (source_size[0] / source_size[1]) - 1.)
    x, y = [gaussian_gradient_magnitude(rgb @ _LUMA, sigma=1.2).ravel() for rgb in (first, second)]
    x = x - x.mean()
    y = y - y.mean()
    norm = float(np.linalg.norm(x) * np.linalg.norm(y))
    correlation = float(np.clip(np.dot(x, y) / norm, -1., 1.)) if norm > 1e-12 else None
    return {
        "passed": bool(aspect_error <= max_aspect_error and correlation is not None and correlation >= min_edge_correlation),
        "aspect_ratio_error": aspect_error,
        "edge_correlation": correlation,
        "source_size": list(source_size),
        "reference_size": list(reference_size),
        "working_size": [first.shape[1], first.shape[0]],
        "max_aspect_error": max_aspect_error,
        "min_edge_correlation": min_edge_correlation,
    }


def srgb_to_cielab(rgb):
    """SDR encoded sRGB [0,1] to CIE L*a*b* using a D65 reference white."""
    linear = np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)
    relative_xyz = (linear @ _SRGB_TO_XYZ.T) / _D65_WHITE
    delta = 6. / 29.
    f = np.where(relative_xyz > delta**3, np.cbrt(relative_xyz), relative_xyz / (3. * delta**2) + 4. / 29.)
    fx, fy, fz = np.moveaxis(f, -1, 0)
    return np.stack((116. * fy - 16., 500. * (fx - fy), 200. * (fy - fz)), axis=-1)


def ciede2000(first, second):
    """CIEDE2000 with unit parametric weights, in the Sharma–Wu–Dalal form."""
    l1, a1, b1 = np.moveaxis(np.asarray(first, dtype=np.float64), -1, 0)
    l2, a2, b2 = np.moveaxis(np.asarray(second, dtype=np.float64), -1, 0)
    c_mean = (np.hypot(a1, b1) + np.hypot(a2, b2)) / 2.
    c7 = c_mean**7
    g = .5 * (1. - np.sqrt(c7 / (c7 + 25.**7)))
    a1p, a2p = (1. + g) * a1, (1. + g) * a2
    c1p, c2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.mod(np.degrees(np.arctan2(b1, a1p)), 360.)
    h2p = np.mod(np.degrees(np.arctan2(b2, a2p)), 360.)
    nonzero_chroma = (c1p * c2p) > 0.
    hue_difference = h2p - h1p
    # Stabilize the published 180° boundary against floating-point roundoff.
    short_arc = np.abs(hue_difference) <= 180. + 1e-12
    hue_delta = np.where(
        nonzero_chroma,
        np.where(short_arc, hue_difference, hue_difference - np.copysign(360., hue_difference)),
        0.,
    )
    big_hue_delta = 2. * np.sqrt(c1p * c2p) * np.sin(np.radians(hue_delta / 2.))
    l_mean, c_mean_p = (l1 + l2) / 2., (c1p + c2p) / 2.
    h_sum = h1p + h2p
    hue_mean = np.where(
        nonzero_chroma,
        np.where(short_arc, h_sum / 2., (h_sum + np.where(h_sum < 360., 360., -360.)) / 2.),
        h_sum,
    )
    t = (
        1.
        - .17 * np.cos(np.radians(hue_mean - 30.))
        + .24 * np.cos(np.radians(2. * hue_mean))
        + .32 * np.cos(np.radians(3. * hue_mean + 6.))
        - .20 * np.cos(np.radians(4. * hue_mean - 63.))
    )
    l_squared = (l_mean - 50.)**2
    s_l = 1. + .015 * l_squared / np.sqrt(20. + l_squared)
    s_c = 1. + .045 * c_mean_p
    s_h = 1. + .015 * c_mean_p * t
    c7_p = c_mean_p**7
    delta_theta = 30. * np.exp(-((hue_mean - 275.) / 25.)**2)
    r_t = -2. * np.sqrt(c7_p / (c7_p + 25.**7)) * np.sin(np.radians(2. * delta_theta))
    v_l, v_c, v_h = (l2 - l1) / s_l, (c2p - c1p) / s_c, big_hue_delta / s_h
    return np.sqrt(np.maximum(v_l**2 + v_c**2 + v_h**2 + r_t * v_c * v_h, 0.))


def _mean_delta_e00(first, second):
    total = 0.
    for start in range(0, first.shape[0], 128):
        stop = start + 128
        delta = ciede2000(srgb_to_cielab(first[start:stop]), srgb_to_cielab(second[start:stop]))
        total += float(delta.sum())
    return total / (first.shape[0] * first.shape[1])


def _ssim(x, y):
    def smooth(array):
        return gaussian_filter(array, sigma=1.5, truncate=3.5, mode="reflect")

    mean_x, mean_y = smooth(x), smooth(y)
    var_x = np.maximum(smooth(x * x) - mean_x**2, 0.)
    var_y = np.maximum(smooth(y * y) - mean_y**2, 0.)
    covariance = smooth(x * y) - mean_x * mean_y
    c1, c2 = .01**2, .03**2
    local = ((2. * mean_x * mean_y + c1) * (2. * covariance + c2)) / (
        (mean_x**2 + mean_y**2 + c1) * (var_x + var_y + c2)
    )
    if min(x.shape) > 10:
        local = local[5:-5, 5:-5]
    return float(np.clip(local.mean(), -1., 1.))


def _oklab_swd(first, second):
    n = first.shape[0] * first.shape[1]
    # A fixed, repeatable sample and nearly equal-area spherical directions.
    # Include all pixels for small inputs, so permutation invariance is exact there.
    indices = np.linspace(0, n - 1, min(n, 8192), dtype=np.intp)
    x = to_oklab(first.reshape(-1, 3)[indices])
    y = to_oklab(second.reshape(-1, 3)[indices])
    step = np.arange(32, dtype=np.float64)
    z = 1. - 2. * (step + .5) / len(step)
    angle = np.pi * (3. - np.sqrt(5.)) * step
    radial = np.sqrt(1. - z**2)
    directions = np.stack((radial * np.cos(angle), radial * np.sin(angle), z))
    sorted_x, sorted_y = np.sort(x @ directions, axis=0), np.sort(y @ directions, axis=0)
    return float(np.mean(np.abs(sorted_x - sorted_y)))


def measure_losses(reference, lut_result, *, max_edge=768):
    """Four unweighted losses, all lower-is-closer. Geometry screening is separate."""
    first, second, _, _ = _pair(reference, lut_result, max_edge)
    return {
        "rgb_l1": float(np.mean(np.abs(first - second))),
        "delta_e00": _mean_delta_e00(first, second),
        "luma_dssim": 1. - _ssim(first @ _LUMA, second @ _LUMA),
        "oklab_swd": _oklab_swd(first, second),
        "working_size": [first.shape[1], first.shape[0]],
    }

