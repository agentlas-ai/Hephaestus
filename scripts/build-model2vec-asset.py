#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import mmap
import shutil
import struct
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# Two model profiles. potion-base-8M is distilled from an English BERT: its
# vocabulary has no whole Hangul syllables, only Jamo, so WordPiece shatters
# Korean into individual letters and the resulting cosine measures letter
# frequency rather than meaning. Measured on a fixed ranking set it scored 0/4
# while potion-multilingual-128M scored 3/4, and cross-lingual similarity went
# from -0.03 (worse than random) to 0.494. The multilingual asset is distilled
# from BAAI/bge-m3 and carries a Unigram tokenizer, which is why the tokenizer
# type is part of the profile rather than assumed.
MODEL_PROFILES: dict[str, dict[str, Any]] = {
    "potion-base-8M-int8": {
        "modelId": "minishlab/potion-base-8M",
        "revision": "bf8b056651a2c21b8d2565580b8569da283cab23",
        "vocabSize": 29528,
        "tokenizerType": "WordPiece",
        "engine": "agentlas_pure_python_wordpiece_v1",
        "files": {
            "config.json": {
                "sha256": "2a6ac0e9aaa356a68a5688070db78fc3a464fefe85d2f06a1905ce3718687553",
                "size": 202,
            },
            "tokenizer.json": {
                "sha256": "e67e803f624fb4d67dea1c730d06e1067e1b14d830e2c2202569e3ef0f70bb50",
                "size": 683666,
            },
            "model.safetensors": {
                "sha256": "f65d0f325faadc1e121c319e2faa41170d3fa07d8c89abd48ca5358d9a223de2",
                "size": 30236760,
            },
            "README.md": {
                "sha256": "de8ec91bf63c5f4c0e20751c227b2d049953e1cab5f8d5d44211c59a44795bdd",
                "size": 5203,
            },
        },
    },
    "potion-multilingual-128M-int8": {
        "modelId": "minishlab/potion-multilingual-128M",
        "revision": "73908c3438cf03b6a01bcb9611d62b23d0726f08",
        "vocabSize": 500353,
        "tokenizerType": "Unigram",
        "engine": "agentlas_pure_python_unigram_v1",
        "files": {
            "config.json": {
                "sha256": "595e4cab2093732efd5dbe084fd5c1826b5eea693b73b4c1fd971672867d2e54",
                "size": 271,
            },
            "tokenizer.json": {
                "sha256": "19f1909063da3cfe3bd83a782381f040dccea475f4816de11116444a73e1b6a1",
                "size": 18616131,
            },
            "model.safetensors": {
                "sha256": "14b5eb39cb4ce5666da8ad1f3dc6be4346e9b2d601c073302fa0a31bf7943397",
                "size": 512361560,
            },
            "README.md": {
                "sha256": "9505454b6a3efbb25257124de875cb73e02bd663a822528525a3c29b1c4d91ac",
                "size": 5575,
            },
        },
    },
}
DEFAULT_MODEL = "potion-multilingual-128M-int8"
DEFAULT_OUTPUT = ROOT / "assets" / "model2vec" / DEFAULT_MODEL
SOURCE_MODEL_ID = MODEL_PROFILES[DEFAULT_MODEL]["modelId"]
SOURCE_REVISION = MODEL_PROFILES[DEFAULT_MODEL]["revision"]
DIMENSIONS = 256
ASSET_FORMAT = "agentlas-model2vec-int8-v1"
EMBEDDING_PART_MAX_BYTES = 64 * 1024 * 1024
# The exact tokenizer each asset is read with. Agentlas reimplements these in
# TypeScript and Python rather than depending on the tokenizers library, so the
# contract is pinned here and asserted by the parity gate.
TOKENIZER_CONTRACTS: dict[str, dict[str, Any]] = {
    "WordPiece": {
        "type": "WordPiece",
        "normalizer": "BertNormalizer(lowercase=true,handle_chinese_chars=true)",
        "preTokenizer": "BertPreTokenizer",
        "continuingSubwordPrefix": "##",
        "unknownToken": "[UNK]",
        "addSpecialTokens": False,
    },
    "Unigram": {
        "type": "Unigram",
        # bge-m3's normalizer is a 316KB precompiled SentencePiece charsmap.
        # NFKC plus whitespace collapsing reproduces it for the text this runs
        # on, which is why the charsmap does not have to be reimplemented.
        "normalizer": "NFKC + collapse whitespace",
        "preTokenizer": "Metaspace(replacement=U+2581,prepend_scheme=always)",
        "segmentation": "viterbi_max_log_prob",
        "unknownToken": "[UNK]",
        "addSpecialTokens": False,
    },
}
LICENSE_BODY = """MIT License

Copyright (c) 2024 Thomas van Dongen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the \"Software\"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or verify a pinned dependency-free Agentlas Model2Vec int8 release asset"
    )
    parser.add_argument("--model", choices=sorted(MODEL_PROFILES), default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--source-cache", type=Path)
    parser.add_argument(
        "--prebuilt-asset",
        type=Path,
        help="Verified unsplit quantized asset to deterministically repartition after source-cache validation",
    )
    parser.add_argument("--offline", action="store_true", help="Require all pinned upstream files in --source-cache")
    parser.add_argument("--check", action="store_true", help="Verify the existing release asset without network access")
    args = parser.parse_args()
    if args.output is None:
        args.output = ROOT / "assets" / "model2vec" / args.model
    if args.check:
        from ontology.model_assets import verify_model_asset

        asset = verify_model_asset(args.output)
        print(
            json.dumps(
                {
                    "status": "pass",
                    "path": str(asset.path),
                    "identity": asset.identity,
                    "contentSha256": asset.content_sha256,
                },
                sort_keys=True,
            )
        )
        return 0

    if args.source_cache:
        source_root = args.source_cache.expanduser().resolve()
        source_root.mkdir(parents=True, exist_ok=True)
        build(
            source_root,
            args.output.expanduser().resolve(),
            offline=args.offline,
            model=args.model,
            prebuilt_asset=args.prebuilt_asset,
        )
    else:
        if args.offline:
            parser.error("--offline requires --source-cache")
        if args.prebuilt_asset:
            parser.error("--prebuilt-asset requires --source-cache so pinned provenance is checked independently")
        with tempfile.TemporaryDirectory(prefix="agentlas-model2vec-source-") as temporary:
            build(Path(temporary), args.output.expanduser().resolve(), offline=False, model=args.model)
    return 0


def build(
    source_root: Path,
    output: Path,
    *,
    offline: bool,
    model: str = DEFAULT_MODEL,
    prebuilt_asset: Path | None = None,
) -> None:
    profile = MODEL_PROFILES[model]
    for name, record in profile["files"].items():
        source = source_root / name
        if not source.exists():
            if offline:
                raise SystemExit(f"offline source file missing: {source}")
            _download_source(name, source, model_id=profile["modelId"], revision=profile["revision"])
        _verify_file(source, record)

    config = json.loads((source_root / "config.json").read_text(encoding="utf-8"))
    tokenizer = json.loads((source_root / "tokenizer.json").read_text(encoding="utf-8"))
    tokenizer_model = tokenizer.get("model") or {}
    vocab = tokenizer_model.get("vocab")
    # WordPiece stores {token: id}; Unigram stores [[token, log_prob], ...]. The
    # shape is part of the pinned contract, so check it rather than infer it.
    expected_container = dict if profile["tokenizerType"] == "WordPiece" else list
    if (
        config.get("hidden_dim") != DIMENSIONS
        or tokenizer_model.get("type") != profile["tokenizerType"]
        or not isinstance(vocab, expected_container)
        or len(vocab) != profile["vocabSize"]
    ):
        raise SystemExit("pinned config/tokenizer shape contract changed")

    output.mkdir(parents=True, exist_ok=True)
    _clear_embedding_outputs(output)
    scales_path = output / "scales.f32le"
    if prebuilt_asset is not None:
        embedding_parts = _emit_prebuilt_asset(
            prebuilt_asset.expanduser().resolve(),
            output,
            profile=profile,
            model=model,
        )
    else:
        embedding_parts = _quantize_safetensors(
            source_root / "model.safetensors",
            output,
            scales_path,
            vocab_size=profile["vocabSize"],
            split_embeddings=profile["tokenizerType"] == "Unigram",
        )
        shutil.copyfile(source_root / "tokenizer.json", output / "tokenizer.json")
        (output / "LICENSE.model.txt").write_text(
            _license_text(model, profile),
            encoding="utf-8",
        )

    payload_names = [*embedding_parts, "scales.f32le", "tokenizer.json", "LICENSE.model.txt"]
    files = {
        name: {"sha256": _sha256_file(output / name), "size": (output / name).stat().st_size}
        for name in payload_names
    }
    manifest = {
        "schemaVersion": "1.0",
        "format": ASSET_FORMAT,
        "modelName": model,
        "dimensions": DIMENSIONS,
        "vocabSize": profile["vocabSize"],
        "source": {
            "modelId": profile["modelId"],
            "revision": profile["revision"],
            "files": profile["files"],
        },
        "license": {"spdx": "MIT", "file": "LICENSE.model.txt"},
        "tokenizer": TOKENIZER_CONTRACTS[profile["tokenizerType"]],
        "quantization": {
            "scheme": "symmetric_per_row_int8",
            "dtype": "int8",
            "scaleDtype": "float32le",
            "formula": "q=round(value/(max_abs(row)/127)); reconstructed=q*scale",
        },
        "runtime": {
            "engine": profile["engine"],
            "networkRequired": False,
            "externalPackages": [],
        },
        "files": files,
        "contentSha256": _content_identity(files),
    }
    if profile["tokenizerType"] == "Unigram":
        manifest["embeddingParts"] = embedding_parts
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    from ontology.model_assets import verify_model_asset

    asset = verify_model_asset(output)
    print(
        json.dumps(
            {
                "status": "built",
                "path": str(asset.path),
                "identity": asset.identity,
                "payloadBytes": sum(record["size"] for record in files.values()),
            },
            sort_keys=True,
        )
    )


def _download_source(
    name: str,
    destination: Path,
    *,
    model_id: str = SOURCE_MODEL_ID,
    revision: str = SOURCE_REVISION,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://huggingface.co/{model_id}/resolve/{revision}/{name}?download=true"
    temporary = destination.with_suffix(destination.suffix + ".download")
    try:
        with urllib.request.urlopen(url, timeout=120) as response, open(temporary, "wb") as handle:
            while block := response.read(1024 * 1024):
                handle.write(block)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def _quantize_safetensors(
    source: Path,
    output: Path,
    scales_output: Path,
    *,
    vocab_size: int,
    split_embeddings: bool,
) -> list[str]:
    with open(source, "rb") as source_handle, mmap.mmap(source_handle.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
        header_size = struct.unpack_from("<Q", mapped, 0)[0]
        header = json.loads(mapped[8 : 8 + header_size])
        tensor = header.get("embeddings")
        if tensor != {
            "dtype": "F32",
            "shape": [vocab_size, DIMENSIONS],
            "data_offsets": [0, vocab_size * DIMENSIONS * 4],
        }:
            raise SystemExit(f"unexpected pinned safetensors layout: {tensor!r}")
        data_start = 8 + header_size
        unpack_row = struct.Struct(f"<{DIMENSIONS}f")
        pack_scale = struct.Struct("<f")
        rows_per_part = EMBEDDING_PART_MAX_BYTES // DIMENSIONS
        embedding_parts: list[str] = []
        embeddings = None
        try:
            with open(scales_output, "wb") as scales:
                for row_index in range(vocab_size):
                    if embeddings is None or (split_embeddings and row_index % rows_per_part == 0):
                        if embeddings is not None:
                            embeddings.close()
                        part_index = len(embedding_parts)
                        name = f"embeddings.i8.part-{part_index:03d}" if split_embeddings else "embeddings.i8"
                        embedding_parts.append(name)
                        embeddings = open(output / name, "wb")
                    values = unpack_row.unpack_from(mapped, data_start + (row_index * unpack_row.size))
                    max_abs = max(abs(value) for value in values)
                    scale = max_abs / 127.0 if max_abs > 0.0 else 1.0
                    if not math.isfinite(scale) or scale <= 0.0:
                        raise SystemExit(f"invalid quantization scale at row {row_index}")
                    quantized = bytearray(DIMENSIONS)
                    for index, value in enumerate(values):
                        integer = max(-127, min(127, round(value / scale)))
                        quantized[index] = integer & 0xFF
                    assert embeddings is not None
                    embeddings.write(quantized)
                    scales.write(pack_scale.pack(scale))
        finally:
            if embeddings is not None:
                embeddings.close()
    _validate_embedding_parts(output, embedding_parts, vocab_size=vocab_size, split_embeddings=split_embeddings)
    if scales_output.stat().st_size != vocab_size * 4:
        raise SystemExit("scale output size mismatch")
    return embedding_parts


def _clear_embedding_outputs(output: Path) -> None:
    (output / "embeddings.i8").unlink(missing_ok=True)
    for path in output.glob("embeddings.i8.part-*"):
        if path.is_file() or path.is_symlink():
            path.unlink()


def _emit_prebuilt_asset(
    source: Path,
    output: Path,
    *,
    profile: dict[str, Any],
    model: str,
) -> list[str]:
    manifest_path = source / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid prebuilt asset manifest: {manifest_path}") from exc
    expected_source = {
        "modelId": profile["modelId"],
        "revision": profile["revision"],
        "files": profile["files"],
    }
    if (
        manifest.get("format") != ASSET_FORMAT
        or manifest.get("modelName") != model
        or manifest.get("dimensions") != DIMENSIONS
        or manifest.get("vocabSize") != profile["vocabSize"]
        or manifest.get("source") != expected_source
        or manifest.get("tokenizer") != TOKENIZER_CONTRACTS[profile["tokenizerType"]]
        or manifest.get("runtime")
        != {"engine": profile["engine"], "networkRequired": False, "externalPackages": []}
    ):
        raise SystemExit("prebuilt asset does not match the independently pinned source/runtime contract")
    files = manifest.get("files")
    required = {"embeddings.i8", "scales.f32le", "tokenizer.json", "LICENSE.model.txt"}
    if not isinstance(files, dict) or set(files) != required:
        raise SystemExit("prebuilt asset must contain exactly one unsplit embeddings payload and its metadata")
    for name in sorted(required):
        _verify_file(source / name, files[name])
    if manifest.get("contentSha256") != _content_identity(files):
        raise SystemExit("prebuilt asset contentSha256 does not match its payload records")
    if files["embeddings.i8"]["size"] != profile["vocabSize"] * DIMENSIONS:
        raise SystemExit("prebuilt int8 embedding size mismatch")
    if files["scales.f32le"]["size"] != profile["vocabSize"] * 4:
        raise SystemExit("prebuilt scale size mismatch")

    split_embeddings = profile["tokenizerType"] == "Unigram"
    if split_embeddings:
        embedding_parts = _split_embeddings(
            source / "embeddings.i8",
            output,
            vocab_size=profile["vocabSize"],
        )
    else:
        shutil.copyfile(source / "embeddings.i8", output / "embeddings.i8")
        embedding_parts = ["embeddings.i8"]
    for name in ("scales.f32le", "tokenizer.json", "LICENSE.model.txt"):
        shutil.copyfile(source / name, output / name)
    _validate_embedding_parts(
        output,
        embedding_parts,
        vocab_size=profile["vocabSize"],
        split_embeddings=split_embeddings,
    )
    return embedding_parts


def _split_embeddings(source: Path, output: Path, *, vocab_size: int) -> list[str]:
    expected_size = vocab_size * DIMENSIONS
    if source.stat().st_size != expected_size:
        raise SystemExit("prebuilt int8 embedding size mismatch")
    names: list[str] = []
    with open(source, "rb") as input_handle:
        while block := input_handle.read(EMBEDDING_PART_MAX_BYTES):
            if len(block) % DIMENSIONS != 0:
                raise SystemExit("embedding split is not row-aligned")
            name = f"embeddings.i8.part-{len(names):03d}"
            with open(output / name, "wb") as part:
                part.write(block)
            names.append(name)
    _validate_embedding_parts(output, names, vocab_size=vocab_size, split_embeddings=True)
    return names


def _validate_embedding_parts(
    output: Path,
    names: list[str],
    *,
    vocab_size: int,
    split_embeddings: bool,
) -> None:
    expected_count = math.ceil((vocab_size * DIMENSIONS) / EMBEDDING_PART_MAX_BYTES) if split_embeddings else 1
    expected_names = (
        [f"embeddings.i8.part-{index:03d}" for index in range(expected_count)]
        if split_embeddings
        else ["embeddings.i8"]
    )
    if names != expected_names:
        raise SystemExit(f"unexpected embedding part sequence: {names!r}")
    combined_size = 0
    for index, name in enumerate(names):
        size = (output / name).stat().st_size
        if size <= 0 or size % DIMENSIONS != 0:
            raise SystemExit(f"embedding part is not row-aligned: {name}")
        if split_embeddings and size > EMBEDDING_PART_MAX_BYTES:
            raise SystemExit(f"embedding part exceeds 64 MiB: {name}")
        if split_embeddings and index < len(names) - 1 and size != EMBEDDING_PART_MAX_BYTES:
            raise SystemExit(f"non-final embedding part is not exactly 64 MiB: {name}")
        combined_size += size
    if combined_size != vocab_size * DIMENSIONS:
        raise SystemExit("combined int8 embedding part size mismatch")


def _license_text(model: str, profile: dict[str, Any]) -> str:
    display_name = "potion-base-8M" if model == "potion-base-8M-int8" else model
    return (
        f"{display_name} model asset\n"
        f"\nSource: https://huggingface.co/{profile['modelId']}"
        f"\nRevision: {profile['revision']}"
        "\nLicense declared by the upstream model card: MIT"
        "\nAuthors: Minish Lab (Stephan Tulkens and Thomas van Dongen)\n\n"
        + LICENSE_BODY
    )


def _verify_file(path: Path, record: dict[str, Any]) -> None:
    if path.stat().st_size != record["size"] or _sha256_file(path) != record["sha256"]:
        raise SystemExit(f"pinned upstream checksum mismatch: {path}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _content_identity(files: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    for name in sorted(files):
        record = files[name]
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(record["sha256"].encode("ascii"))
        digest.update(b"\0")
        digest.update(str(record["size"]).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
