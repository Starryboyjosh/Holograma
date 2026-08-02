"""WAVE-11 (I1): caché de logos correcta y referencias aisladas por etiqueta.

El bug (yolo_instructions.md §4.3 / §13 I1): ``data/logo_index.npz`` solo
guardaba ``meta_sig``/``by_img``/``by_des``. ``_rebuild_logo_templates`` no
reseteaba ``_logo_hsv_hists`` en el bloque de reset y el camino de caché
retornaba antes de poblarlo → en producción ``_logo_hsv_hists`` quedaba vacío
y ``compare_hsv_signature`` hacía fail-open (nunca rechazaba por color).

Estos tests cubren: (1) reset completo; (2) la caché guarda y lee ``by_hsv``
+ ``cache_version``; (3) un npz viejo (sin esas claves) se rechaza y se
reconstruye; (4) el fallback cruzado solo aplica con UNA etiqueta entrenada.
"""

import json
import numpy as np
from pathlib import Path

import vision.person_detector as pd


def _write_metadata(base_dir: Path, labels: list[str]) -> None:
    """Crea ``data/training_metadata.json`` con un thumbnail absoluto por label.

    Se escribe un PNG de color plano (3 canales) por etiqueta para que
    ``_compute_hsv_hist`` tenga material aunque ORB no encuentre keypoints.
    """
    images = base_dir / "images"
    images.mkdir(parents=True, exist_ok=True)
    entries = []
    for i, label in enumerate(labels):
        img = np.zeros((60, 60, 3), dtype=np.uint8)
        img[:, :, 0] = 40 + 40 * (i + 1)  # azul distinto por etiqueta
        img[:, :, 1] = 180
        img[:, :, 2] = 220
        path = images / f"logo_{i}.png"
        import cv2

        cv2.imwrite(str(path), img)
        entries.append(
            {
                "id": 1785600000000 + i,
                "label": label,
                "desc": "synthetic",
                "x": 0,
                "y": 0,
                "w": 0,
                "h": 0,
                "thumbnail": f"/{path.absolute()}",
            }
        )
    (base_dir / "data").mkdir(parents=True, exist_ok=True)
    (base_dir / "data" / "training_metadata.json").write_text(
        json.dumps(entries, ensure_ascii=False), encoding="utf-8"
    )


def _meta_sig(base_dir: Path) -> str:
    meta_path = base_dir / "data" / "training_metadata.json"
    return f"{meta_path.stat().st_mtime_ns}:{meta_path.stat().st_size}"


def _make_detector():
    det = pd.YoloPersonDetector()
    det._load_training_data = lambda: None
    det._maybe_reload_training = lambda: None
    return det


def test_reset_block_clears_hsv_hists():
    """El reset debe vaciar también ``_logo_hsv_hists`` (antes no lo hacía)."""
    det = _make_detector()
    det._logo_hsv_hists = {"Legacy": [np.ones((2, 2))]}
    det._rebuild_logo_templates(base_dir="/nonexistent")
    assert det._logo_hsv_hists == {}


def test_rebuild_writes_hsv_and_cache_version(tmp_path):
    _write_metadata(tmp_path, ["Logo ITEE"])
    det = _make_detector()
    det._rebuild_logo_templates(base_dir=tmp_path)
    # El índice en memoria queda poblado (no solo plantillas/ORB).
    assert set(det._logo_hsv_hists) == {"Logo ITEE"}
    assert len(det._logo_hsv_hists["Logo ITEE"]) >= 1
    assert det._logo_images and det._logo_images["Logo ITEE"]
    # La caché en disco tiene el nuevo esquema.
    cache_path = tmp_path / "data" / "logo_index.npz"
    assert cache_path.is_file()
    cached = np.load(str(cache_path), allow_pickle=True)
    assert set(cached.files) >= {"meta_sig", "cache_version", "by_img", "by_des", "by_hsv"}
    assert int(cached["cache_version"].item()) == pd._LOGO_CACHE_VERSION


def test_cache_load_populates_hsv_hists(tmp_path):
    """El camino de caché debe poblar ``_logo_hsv_hists`` al cargar (el bug)."""
    _write_metadata(tmp_path, ["Logo ITEE"])
    det = _make_detector()
    det._rebuild_logo_templates(base_dir=tmp_path)
    # Segunda instancia: lee de la caché, sin releer los PNG.
    det2 = _make_detector()
    det2._rebuild_logo_templates(base_dir=tmp_path)
    assert set(det2._logo_hsv_hists) == {"Logo ITEE"}
    assert len(det2._logo_hsv_hists["Logo ITEE"]) >= 1


def test_stale_cache_without_hsv_is_rebuilt(tmp_path):
    """Un npz viejo (sin cache_version ni by_hsv) se rechaza y reconstruye."""
    _write_metadata(tmp_path, ["Logo ITEE"])
    sig = _meta_sig(tmp_path)
    cache_path = tmp_path / "data" / "logo_index.npz"
    old = np.asarray(
        {
            "Logo ITEE": [np.ones((8, 8), dtype=np.uint8) * 128],
        },
        dtype=object,
    )
    np.savez_compressed(
        str(cache_path),
        meta_sig=np.asarray(sig),
        by_img=old,
        by_des=old,
    )
    det = _make_detector()
    det._rebuild_logo_templates(base_dir=tmp_path)
    # No cargó el npz viejo a medias: reconstruyó y populó HSV.
    assert set(det._logo_hsv_hists) == {"Logo ITEE"}
    cached = np.load(str(cache_path), allow_pickle=True)
    assert int(cached["cache_version"].item()) == pd._LOGO_CACHE_VERSION
    assert "by_hsv" in cached.files


def test_cross_label_fallback_only_with_single_label():
    """El fallback cruzado (bootstrap) solo aplica con UNA etiqueta entrenada."""
    det = _make_detector()
    det._logo_images = {"Logo ITEE": [np.ones((8, 8), dtype=np.uint8) * 200]}
    det._logo_templates = {}
    det._logo_hsv_hists = {}
    # Una sola etiqueta entrenada: "Uniforme ITEE" puede bootstrap contra ella.
    assert len(det._logo_templates_for("Uniforme ITEE")) == 1
    assert len(det._logo_orb_for("Uniforme ITEE")) == 0  # sin ORB para esa label


def test_orb_reference_upscaled_for_small_crop(tmp_path):
    """Sesión 14: la referencia ORB de un crop pequeño se escala hacia arriba.

    Antes se construía ORB sobre el crop crudo (91×69 → ~15 keypoints) y el
    canal quedaba sin evidencia → el conf efectivo era solo template a 0.42 y
    un bolsillo oscuro (0.473) pasaba. Con el lado mínimo (ORB_REF_MIN) el
    descriptor gana cientos de keypoints y separa genuino (1.0) de falso (0.0).
    """
    import cv2

    images = tmp_path / "images"
    images.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)
    img = np.zeros((69, 91, 3), dtype=np.uint8)
    img[:, :, 0] = 195
    img[:, :, 1] = 167
    img[:, :, 2] = 57
    # Textura (pliegues/texto del logo) para que ORB tenga keypoints.
    cv2.rectangle(img, (10, 10), (70, 55), (200, 200, 200), -1)
    cv2.putText(img, "ITEE", (18, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (40, 40, 90), 3)
    img = np.clip(img.astype(int) + rng.integers(-14, 15, img.shape), 0, 255).astype(np.uint8)
    path = images / "logo_small.png"
    cv2.imwrite(str(path), img)
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "training_metadata.json").write_text(
        json.dumps(
            [
                {
                    "id": 1785600000000,
                    "label": "Logo ITEE",
                    "desc": "small crop",
                    "x": 0,
                    "y": 0,
                    "w": 91,
                    "h": 69,
                    "thumbnail": f"/{path.absolute()}",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    det = _make_detector()
    det._rebuild_logo_templates(base_dir=tmp_path)
    des_list = det._logo_orb_for("Logo ITEE")
    assert des_list, "debe haber descriptores ORB de la referencia"
    n_kp = sum(len(d) for d in des_list if d is not None)
    assert n_kp >= 100, f"referencia ORB con pocos keypoints: {n_kp}"


def test_no_cross_label_fallback_with_two_labels():
    """Con dos escuelas entrenadas, la etiqueta X no casa contra la Y."""
    det = _make_detector()
    det._logo_images = {
        "Logo Colegio A": [np.ones((8, 8), dtype=np.uint8) * 200],
        "Logo Colegio B": [np.ones((8, 8), dtype=np.uint8) * 100],
    }
    det._logo_templates = {}
    det._logo_hsv_hists = {}
    assert det._logo_templates_for("Uniforme ITEE") == []
    # Las etiquetas con sus propias fotos siguen resolviendo directo.
    assert len(det._logo_templates_for("Logo Colegio A")) == 1
    assert len(det._logo_templates_for("Logo Colegio B")) == 1


def test_non_uniform_label_never_uses_cross_fallback():
    det = _make_detector()
    det._logo_images = {"Logo ITEE": [np.ones((8, 8), dtype=np.uint8) * 200]}
    det._logo_templates = {}
    det._logo_hsv_hists = {}
    assert det._logo_templates_for("botella") == []


def test_cache_invalidated_when_image_changes_without_metadata(tmp_path):
    """WAVE-20 (I10): borrar/re-importar la foto sin tocar el metadata invalida.

    La firma de la caché incluye el estado de CADA imagen referenciada
    (mtime_ns + size), no solo del metadata. Si solo cambia el JPEG, el npz
    debe reconstruirse en vez de servir el stale.
    """
    _write_metadata(tmp_path, ["Logo ITEE"])
    det = _make_detector()
    det._rebuild_logo_templates(base_dir=tmp_path)
    cache_path = tmp_path / "data" / "logo_index.npz"
    assert cache_path.is_file()
    cached = np.load(str(cache_path), allow_pickle=True)
    sig_before = str(cached["meta_sig"].item())

    # Reescribir el PNG (mismo nombre y metadata, contenido/size/mtime nuevos).
    image_path = tmp_path / "images" / "logo_0.png"
    import cv2

    img = np.zeros((90, 90, 3), dtype=np.uint8)
    img[:, :, 0] = 90
    img[:, :, 1] = 90
    img[:, :, 2] = 220
    cv2.imwrite(str(image_path), img)

    det2 = _make_detector()
    det2._rebuild_logo_templates(base_dir=tmp_path)
    cached2 = np.load(str(cache_path), allow_pickle=True)
    sig_after = str(cached2["meta_sig"].item())
    assert sig_after != sig_before
    # Reconstruyó en vez de servir el npz stale.
    assert set(det2._logo_hsv_hists) == {"Logo ITEE"}
    assert len(det2._logo_hsv_hists["Logo ITEE"]) >= 1
    assert len(det2._logo_images["Logo ITEE"]) == 1


def test_cache_invalidated_when_image_missing(tmp_path):
    """WAVE-20 (I10): si una imagen referenciada falta, no sirve el npz stale."""
    _write_metadata(tmp_path, ["Logo ITEE"])
    det = _make_detector()
    det._rebuild_logo_templates(base_dir=tmp_path)
    cache_path = tmp_path / "data" / "logo_index.npz"
    assert cache_path.is_file()

    image_path = tmp_path / "images" / "logo_0.png"
    image_path.unlink()

    det2 = _make_detector()
    det2._rebuild_logo_templates(base_dir=tmp_path)
    # Imagen inexistente: la etiqueta queda sin plantillas/HSV (no carga lo
    # que quedó del npz stale).
    assert set(det2._logo_hsv_hists) == set()
    assert set(det2._logo_images) == set()
    assert set(det2._logo_templates) == set()
