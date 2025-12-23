import cv2
import numpy as np
import os
import sys

def adaptive_gamma(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mean = np.mean(gray)

    gamma = np.interp(mean, [50, 200], [1.6, 0.9])
    gamma = np.clip(gamma, 0.85, 1.6)

    lut = np.array(
        [(i / 255.0) ** (1 / gamma) * 255 for i in range(256)],
        dtype="uint8"
    )

    return cv2.LUT(img, lut), gamma


def detect_face_bbox(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)
    )

    if len(faces) == 0:
        return None

    return max(faces, key=lambda b: b[2] * b[3])  # biggest face

def extract_foreground(img):
    mask = np.zeros(img.shape[:2], np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)

    face = detect_face_bbox(img)

    if face is None:
        rect = (10, 10, img.shape[1] - 20, img.shape[0] - 20)
    else:
        x, y, w, h = face
        rect = (
            max(x - w, 0),
            max(y - h, 0),
            min(2 * w, img.shape[1] - x),
            min(2 * h, img.shape[0] - y),
        )

    cv2.grabCut(
        img, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT
    )

    output_mask = np.where(
        (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0
    ).astype("float32")

    output_mask = cv2.GaussianBlur(output_mask, (21, 21), 0)
    return np.dstack([output_mask] * 3)

def apply_bokeh(img, mask):
    bg = cv2.GaussianBlur(img, (61, 61), 0)
    return (img * mask + bg * (1 - mask)).astype(np.uint8)


def enhance_texture(img):
    denoise = cv2.fastNlMeansDenoisingColored(
        img, None, 6, 6, 7, 21
    )

    smooth = cv2.bilateralFilter(
        denoise, d=7, sigmaColor=60, sigmaSpace=60
    )

    blur = cv2.GaussianBlur(smooth, (0, 0), 1.1)
    sharp = cv2.addWeighted(smooth, 1.5, blur, -0.5, 0)

    return sharp


def enhance_contrast(img):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(
        clipLimit=2.4, tileGridSize=(8, 8)
    )
    l = clahe.apply(l)

    merged = cv2.merge((l, a, b))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

def generate_studio_portrait(image_path):
    img = cv2.imread(image_path)

    if img is None:
        print("Image not found")
        sys.exit(1)

    mask = extract_foreground(img)
    portrait = apply_bokeh(img, mask)

    textured = enhance_texture(portrait)
    gamma_corrected, gamma = adaptive_gamma(textured)
    final = enhance_contrast(gamma_corrected)

    return final, gamma

if __name__ == "__main__":

    input_image = "/Users/chalspatel/Downloads/pic.jpeg"

    os.makedirs("output_images", exist_ok=True)
    output_path = "output_images/studio_portrait_no_mediapipe.jpg"

    result, gamma_used = generate_studio_portrait(input_image)
    cv2.imwrite(output_path, result)

    print("Studio-quality portrait generated")
    print("Gamma used:", round(gamma_used, 2))
    print("Saved to:", output_path)
