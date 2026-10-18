"""Data loader, pure-stdlib 16-bit PNG heightmap decoder, period resolver, and validator (00_core.md §1)."""

from __future__ import annotations
import hashlib
import json
import math
import os
import struct
import zlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple
from .core import SimError, SimTime, Vec2
from .entities import AccuracyTier, AiTag, PlayerUnitCategory, TargetTag, TrackQuality
from .terrain import Heightmap, TerrainRules


@dataclass(frozen=True)
class DataError:
    code: str
    file: str
    json_path: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.file} {self.json_path}: {self.detail}"


class DataLoadException(Exception):
    def __init__(self, errors: Sequence[DataError]):
        self.errors: List[DataError] = list(errors)
        super().__init__("\n".join(str(e) for e in self.errors))


class IDataSource:
    def exists(self, rel_path: str) -> bool:
        raise NotImplementedError

    def read_bytes(self, rel_path: str) -> bytes:
        raise NotImplementedError


class FileSystemDataSource(IDataSource):
    def __init__(self, data_root: str):
        self.data_root = os.path.abspath(data_root)

    def _full(self, rel_path: str) -> str:
        return os.path.join(self.data_root, rel_path.replace("/", os.sep))

    def exists(self, rel_path: str) -> bool:
        return os.path.isfile(self._full(rel_path))

    def read_bytes(self, rel_path: str) -> bytes:
        with open(self._full(rel_path), "rb") as f:
            return f.read()


class InMemoryDataSource(IDataSource):
    def __init__(self, files: Mapping[str, bytes | str]):
        self._files: Dict[str, bytes] = {}
        for k, v in files.items():
            norm = k.replace("\\", "/").lstrip("/")
            self._files[norm] = v.encode("utf-8") if isinstance(v, str) else bytes(v)

    def exists(self, rel_path: str) -> bool:
        return rel_path in self._files

    def read_bytes(self, rel_path: str) -> bytes:
        return self._files[rel_path]


class Png16Decoder:
    """Pure Python 3 stdlib 16-bit grayscale non-interlaced PNG decoder (00_core.md §1.5)."""

    PNG_SIG = b"\x89PNG\r\n\x1a\n"

    @staticmethod
    def _paeth(a: int, b: int, c: int) -> int:
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        if pb <= pc:
            return b
        return c

    @staticmethod
    def decode(
        data: bytes,
        meters_per_pixel: float,
        min_elevation_m: float,
        max_elevation_m: float,
        file_path: str = "",
    ) -> Heightmap:
        if len(data) < 33 or data[:8] != Png16Decoder.PNG_SIG:
            raise SimError("E_PNG_FORMAT", "高程图必须是 16 位灰度、非隔行 PNG：非 PNG 文件", file_path, "$")
        pos = 8
        width = height = 0
        bit_depth = color_type = interlace = -1
        idat_chunks: List[bytes] = []
        seen_ihdr = False
        seen_iend = False

        while pos + 8 <= len(data):
            length = struct.unpack(">I", data[pos : pos + 4])[0]
            ctype = data[pos + 4 : pos + 8]
            pos += 8
            if pos + length + 4 > len(data):
                raise SimError("E_PNG_FORMAT", "高程图必须是 16 位灰度、非隔行 PNG：块截断", file_path, "$")
            chunk_data = data[pos : pos + length]
            pos += length + 4  # skip CRC
            if ctype == b"IHDR":
                if length != 13:
                    raise SimError("E_PNG_FORMAT", "高程图必须是 16 位灰度、非隔行 PNG：IHDR 长度错误", file_path, "$")
                width, height, bit_depth, color_type, comp, filt, interlace = struct.unpack(">IIBBBBB", chunk_data)
                seen_ihdr = True
                if color_type != 0 or bit_depth != 16 or interlace != 0 or comp != 0 or filt != 0 or width <= 0 or height <= 0:
                    raise SimError(
                        "E_PNG_FORMAT",
                        f"高程图必须是 16 位灰度、非隔行 PNG：bitDepth={bit_depth}, colorType={color_type}, interlace={interlace}",
                        file_path,
                        "$",
                    )
            elif ctype == b"IDAT":
                idat_chunks.append(chunk_data)
            elif ctype == b"IEND":
                seen_iend = True
                break

        if not seen_ihdr or not seen_iend or not idat_chunks:
            raise SimError("E_PNG_FORMAT", "高程图必须是 16 位灰度、非隔行 PNG：缺少 IHDR/IDAT/IEND", file_path, "$")

        try:
            raw = zlib.decompress(b"".join(idat_chunks))
        except Exception as exc:
            raise SimError("E_PNG_FORMAT", f"高程图必须是 16 位灰度、非隔行 PNG：{exc}", file_path, "$") from exc

        bpp = 2
        stride = width * bpp
        expected_len = height * (1 + stride)
        if len(raw) != expected_len:
            raise SimError("E_PNG_FORMAT", "高程图必须是 16 位灰度、非隔行 PNG：解压字节数不符", file_path, "$")

        prev_row = bytearray(stride)
        cur_row = bytearray(stride)
        elevations: List[float] = []
        span = max_elevation_m - min_elevation_m
        offset = 0

        for _r in range(height):
            ftype = raw[offset]
            offset += 1
            row_bytes = raw[offset : offset + stride]
            offset += stride
            if ftype == 0:
                cur_row[:] = row_bytes
            elif ftype == 1:
                for i in range(stride):
                    left = cur_row[i - bpp] if i >= bpp else 0
                    cur_row[i] = (row_bytes[i] + left) & 0xFF
            elif ftype == 2:
                for i in range(stride):
                    cur_row[i] = (row_bytes[i] + prev_row[i]) & 0xFF
            elif ftype == 3:
                for i in range(stride):
                    left = cur_row[i - bpp] if i >= bpp else 0
                    up = prev_row[i]
                    cur_row[i] = (row_bytes[i] + ((left + up) >> 1)) & 0xFF
            elif ftype == 4:
                for i in range(stride):
                    left = cur_row[i - bpp] if i >= bpp else 0
                    up = prev_row[i]
                    up_left = prev_row[i - bpp] if i >= bpp else 0
                    cur_row[i] = (row_bytes[i] + Png16Decoder._paeth(left, up, up_left)) & 0xFF
            else:
                raise SimError("E_PNG_FORMAT", f"高程图必须是 16 位灰度、非隔行 PNG：未知过滤器 {ftype}", file_path, "$")

            for c in range(width):
                g = (cur_row[2 * c] << 8) | cur_row[2 * c + 1]
                elev = min_elevation_m + (g / 65535.0) * span
                elevations.append(elev)
            prev_row[:] = cur_row

        return Heightmap(
            width_px=width,
            height_px=height,
            meters_per_pixel=meters_per_pixel,
            min_elevation_m=min_elevation_m,
            max_elevation_m=max_elevation_m,
            elevation_m=elevations,
        )


GLOBAL_FILES: Tuple[Tuple[str, Optional[str]], ...] = (
    ("rules/conventions.json", "conventions"),
    ("units/air_defense.json", None),
    ("units/sensors.json", None),
    ("units/ew.json", None),
    ("units/deception.json", None),
    ("enemies/munitions.json", None),
    ("enemies/platforms.json", None),
    ("support/fighters.json", None),
    ("support/support.json", None),
    ("rules/accuracy.json", "accuracy"),
    ("rules/damage.json", "damage"),
    ("rules/intercept.json", "intercept"),
    ("rules/exposure.json", "exposure"),
    ("rules/emission.json", "emission"),
    ("rules/debris.json", "debris"),
    ("rules/tracks.json", "tracks"),
    ("rules/ew.json", "ew"),
    ("rules/positions.json", "positions"),
    ("rules/support.json", "support"),
    ("rules/economy.json", "economy"),
    ("rules/movement.json", "movement"),
    ("rules/terrain.json", "terrain"),
    ("rules/engagement.json", "engagement"),
    ("rules/civil.json", "civil"),
    ("rules/enemy_ai.json", "enemy_ai"),
    ("rules/commands.json", "commands"),
)

LEVEL_JSON_FILES: Tuple[Tuple[str, Optional[str]], ...] = (
    ("level.json", None),
    ("waves.json", None),
    ("intel.json", "intel"),
    ("events.json", "events"),
    ("map/layers.json", "layers"),
    ("map/structures.json", "structures"),
    ("map/grid.json", "grid"),
    ("map/deploy.json", "deploy"),
)

IGNORED_FIELDS = {"$schema", "_source", "notes", "provisional"}


@dataclass
class GameCatalog:
    conventions: Dict[str, Any] = field(default_factory=dict)
    air_defense_units: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    weapons: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    sensors: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    ew_units: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    deception_units: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    munitions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    platforms: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    fighters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    fighter_weapons: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    support: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    resolved_for_date: str = "2022-02-24"
    provisional_paths: List[str] = field(default_factory=list)

    def get_player_unit_category(self, unit_id: str) -> PlayerUnitCategory:
        if unit_id in self.air_defense_units:
            return PlayerUnitCategory.Fire
        if unit_id in self.sensors:
            return PlayerUnitCategory.Sensor
        if unit_id in self.ew_units:
            return PlayerUnitCategory.Ew
        if unit_id in self.deception_units:
            return PlayerUnitCategory.Deception
        raise KeyError(f"Unknown player unit '{unit_id}'")

    def get_player_unit_def(self, unit_id: str) -> Dict[str, Any]:
        for tbl in (self.air_defense_units, self.sensors, self.ew_units, self.deception_units):
            if unit_id in tbl:
                return tbl[unit_id]
        raise KeyError(f"Unknown player unit '{unit_id}'")


@dataclass
class LevelData:
    id: str
    date: str
    resolved_night_index: Optional[int]
    meta: Dict[str, Any]
    waves: Dict[str, Any]
    intel: Dict[str, Any]
    story_events: Dict[str, Any]
    layers: Dict[str, Any]
    structures: List[Dict[str, Any]]
    grid: Dict[str, Any]
    deploy: Dict[str, Any]
    heightmap: Heightmap
    catalog: GameCatalog
    data_hash: str
    loaded_files: List[str]
    provisional_paths: List[str]
    urban_polygons: List[List[Vec2]] = field(default_factory=list)
    entry_points_by_id: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class DataLoader:
    """Data loader, unit converter, period resolver, and cross-reference validator (00_core.md §1)."""

    @staticmethod
    def compute_data_hash(source: IDataSource, loaded_files: Sequence[str]) -> str:
        h = hashlib.sha256()
        for rel in sorted(loaded_files):
            raw = source.read_bytes(rel)
            if rel.endswith(".json"):
                raw = raw.replace(b"\r\n", b"\n")
            h.update(rel.encode("utf-8"))
            h.update(b"\x00")
            h.update(struct.pack("<q", len(raw)))
            h.update(raw)
        return "sha256:" + h.hexdigest()

    @staticmethod
    def _ym_tuple(date_or_ym: str, file_path: str, json_path: str) -> Tuple[int, int]:
        y, m, _ = SimTime.parse_year_month(date_or_ym, file_path, json_path)
        return (y, m)

    @staticmethod
    def resolve_period_value(
        val: Any,
        level_date: str,
        file_path: str,
        json_path: str,
        errors: List[DataError],
        allow_future_unlock: bool = False,
    ) -> Optional[float]:
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return float(val)
        if not isinstance(val, list):
            errors.append(DataError("E_TYPE", file_path, json_path, "期望 number 或 periodArray"))
            return 0.0
        if len(val) == 0:
            errors.append(DataError("E_RANGE", file_path, json_path, "取值 0 超出范围 minItems 1"))
            return 0.0
        lvl_ym = DataLoader._ym_tuple(level_date, file_path, json_path)
        prev_ym: Optional[Tuple[int, int]] = None
        chosen: Optional[float] = None
        first_from_str = ""
        first_ym: Optional[Tuple[int, int]] = None
        for idx, item in enumerate(val):
            from_str = item["from"]
            ym = DataLoader._ym_tuple(from_str, file_path, f"{json_path}[{idx}].from")
            if idx == 0:
                first_from_str = from_str
                first_ym = ym
            if prev_ym is not None and ym <= prev_ym:
                errors.append(DataError("E_PERIOD_ORDER", file_path, json_path, "时期数组的 from 必须严格升序"))
                return 0.0
            prev_ym = ym
            if ym <= lvl_ym:
                chosen = float(item["value"])
        if chosen is None:
            if allow_future_unlock and first_ym is not None and first_ym > (2022, 2) and lvl_ym >= (2022, 2):
                return None
            errors.append(
                DataError(
                    "E_PERIOD_BEFORE_FIRST",
                    file_path,
                    json_path,
                    f"关卡日期 {level_date} 早于第一个时期 {first_from_str}",
                )
            )
            return 0.0
        return chosen

    @staticmethod
    def resolve_period_table(
        rows: Sequence[Dict[str, Any]],
        level_date: str,
        file_path: str,
        json_path: str,
        errors: List[DataError],
        allow_fallback_none: bool = False,
    ) -> Optional[Dict[str, Any]]:
        if not rows:
            errors.append(DataError("E_RANGE", file_path, json_path, "取值 0 超出范围 minItems 1"))
            return None
        lvl_ym = DataLoader._ym_tuple(level_date, file_path, json_path)
        prev_ym: Optional[Tuple[int, int]] = None
        chosen: Optional[Dict[str, Any]] = None
        first_from = rows[0]["from"]
        for idx, row in enumerate(rows):
            ym = DataLoader._ym_tuple(row["from"], file_path, f"{json_path}[{idx}].from")
            if prev_ym is not None and ym <= prev_ym:
                errors.append(DataError("E_PERIOD_ORDER", file_path, json_path, "时期数组的 from 必须严格升序"))
                return None
            prev_ym = ym
            if ym <= lvl_ym:
                chosen = dict(row)
        if chosen is None and not allow_fallback_none:
            errors.append(
                DataError(
                    "E_PERIOD_BEFORE_FIRST",
                    file_path,
                    json_path,
                    f"关卡日期 {level_date} 早于第一个时期 {first_from}",
                )
            )
        return chosen

    @staticmethod
    def is_gate_active(
        from_ym: Optional[str],
        until_ym: Optional[str],
        level_date: str,
        file_path: str = "",
        json_path: str = "",
    ) -> bool:
        lvl = DataLoader._ym_tuple(level_date, file_path, json_path)
        if from_ym is not None:
            f_ym = DataLoader._ym_tuple(from_ym, file_path, json_path)
            if lvl < f_ym:
                return False
        if until_ym is not None:
            u_ym = DataLoader._ym_tuple(until_ym, file_path, json_path)
            if lvl >= u_ym:
                return False
        return True

    @staticmethod
    def _convert_leaf_or_minmax(val: Any, factor_mul: float, factor_div: float = 1.0) -> Any:
        if val is None or isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            res = float(val) * factor_mul
            if factor_div != 1.0:
                res = res / factor_div
            return res
        if isinstance(val, dict):
            return {k: DataLoader._convert_leaf_or_minmax(v, factor_mul, factor_div) for k, v in val.items()}
        if isinstance(val, list):
            return [DataLoader._convert_leaf_or_minmax(v, factor_mul, factor_div) for v in val]
        return val

    @staticmethod
    def convert_units_tree(
        node: Any,
        conventions: Dict[str, Any],
        file_path: str = "",
        json_path: str = "$",
        provisional_out: Optional[List[str]] = None,
        errors: Optional[List[DataError]] = None,
    ) -> Any:
        if isinstance(node, list):
            return [
                DataLoader.convert_units_tree(item, conventions, file_path, f"{json_path}[{i}]", provisional_out, errors)
                for i, item in enumerate(node)
            ]
        if not isinstance(node, dict):
            return node

        g2w = float(conventions.get("gameSecToWorldSec", 60.0))
        cell_km = float(conventions.get("cellKm", 1.0))
        mach_kmh = float(conventions.get("machKmh", 1200.0))

        out: Dict[str, Any] = {}
        for k, v in node.items():
            if k == "provisional" and isinstance(v, dict) and provisional_out is not None:
                for pk in v.keys():
                    provisional_out.append(f"{file_path}#{pk}")
            if k in IGNORED_FIELDS:
                continue

            child_path = f"{json_path}.{k}"
            conv_v = DataLoader.convert_units_tree(v, conventions, file_path, child_path, provisional_out, errors)

            if isinstance(conv_v, dict) and set(conv_v.keys()) == {"min", "max"}:
                if float(conv_v["min"]) > float(conv_v["max"]) and errors is not None:
                    errors.append(DataError("E_RANGE", file_path, child_path, f"取值 min {conv_v['min']} > max {conv_v['max']}"))

            out[k] = conv_v
            # Also store converted internal unit keys for seamless access
            if k in ("configurableOnOffGameSec", "configurableOnOff"):
                out["configurableOnOff"] = bool(conv_v)
            elif k in ("offsetCellsAdd", "offsetAddCells"):
                out["offsetAddM"] = DataLoader._convert_leaf_or_minmax(conv_v, cell_km * 1000.0)
            elif k in ("sensorExposureLevelRates", "sensorExposureLevelRatesPerGameSec"):
                out["sensorExposureLevelRatesPerSec"] = DataLoader._convert_leaf_or_minmax(conv_v, 1.0, g2w)
            elif k in ("ewExposureLevelRates", "ewExposureLevelRatesPerGameSec"):
                out["ewExposureLevelRatesPerSec"] = DataLoader._convert_leaf_or_minmax(conv_v, 1.0, g2w)
            elif k.endswith("PerGameSec"):
                new_k = k[: -len("PerGameSec")] + "PerSec"
                out[new_k] = DataLoader._convert_leaf_or_minmax(conv_v, 1.0, g2w)
            elif k == "gameSec":
                out["sec"] = DataLoader._convert_leaf_or_minmax(conv_v, g2w)
            elif k.endswith("GameSec"):
                new_k = k[: -len("GameSec")] + "Sec"
                out[new_k] = DataLoader._convert_leaf_or_minmax(conv_v, g2w)
            elif "GameSec" in k:
                new_k = k.replace("GameSec", "Sec")
                out[new_k] = DataLoader._convert_leaf_or_minmax(conv_v, g2w)
            elif k.endswith("Kmh") and k != "machKmh":
                new_k = k[: -len("Kmh")] + "Mps"
                out[new_k] = DataLoader._convert_leaf_or_minmax(conv_v, 1.0, 3.6)
            elif k.endswith("Km") and k != "cellKm":
                new_k = k[: -len("Km")] + "M"
                out[new_k] = DataLoader._convert_leaf_or_minmax(conv_v, 1000.0)
            elif k.endswith("Cells"):
                new_k = k[: -len("Cells")] + "M"
                out[new_k] = DataLoader._convert_leaf_or_minmax(conv_v, cell_km * 1000.0)
            elif k.endswith("Mach"):
                new_k = k[: -len("Mach")] + "Mps"
                out[new_k] = DataLoader._convert_leaf_or_minmax(conv_v, mach_kmh, 3.6)
            elif k.endswith("Pct"):
                new_k = k[: -len("Pct")] + "Frac"
                out[new_k] = DataLoader._convert_leaf_or_minmax(conv_v, 1.0, 100.0)
            elif k.endswith("Deg"):
                new_k = k[: -len("Deg")] + "Rad"
                out[new_k] = DataLoader._convert_leaf_or_minmax(conv_v, math.pi, 180.0)
            elif k in ("positionM", "posM"):
                if isinstance(conv_v, list) and len(conv_v) == 2:
                    out["pos"] = Vec2(float(conv_v[0]), float(conv_v[1]))
            elif k in ("pathM", "waypointsM", "polygonM") and isinstance(conv_v, list):
                pts = [Vec2(float(p[0]), float(p[1])) for p in conv_v if isinstance(p, list) and len(p) == 2]
                out[k[:-1]] = pts
        return out

    @staticmethod
    def _read_json(source: IDataSource, rel_path: str, expected_kind: Optional[str], errors: List[DataError]) -> Optional[Dict[str, Any]]:
        if not source.exists(rel_path):
            errors.append(DataError("E_FILE_NOT_FOUND", rel_path, "$", "文件不存在"))
            return None
        raw = source.read_bytes(rel_path).decode("utf-8")
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(
                DataError(
                    "E_JSON_SYNTAX",
                    rel_path,
                    "$",
                    f"JSON 语法错误（第 {exc.lineno} 行，第 {exc.colno} 列）：{exc.msg}",
                )
            )
            return None
        if not isinstance(doc, dict):
            errors.append(DataError("E_TYPE", rel_path, "$", "期望 object"))
            return None
        if expected_kind is not None:
            actual_kind = doc.get("kind")
            if actual_kind != expected_kind:
                errors.append(DataError("E_KIND", rel_path, "$.kind", f'kind 应为 "{expected_kind}"，实际 "{actual_kind}"'))
        elif "kind" in doc:
            errors.append(DataError("E_UNKNOWN_FIELD", rel_path, "$.kind", "未知字段"))
        return doc

    @staticmethod
    def load_catalog(
        source: IDataSource,
        level_date: str = "2022-11-15",
        errors_out: Optional[List[DataError]] = None,
        loaded_files_out: Optional[List[str]] = None,
    ) -> GameCatalog:
        errors: List[DataError] = errors_out if errors_out is not None else []
        cat = GameCatalog(resolved_for_date=level_date)
        raw_docs: Dict[str, Dict[str, Any]] = {}

        for rel_path, exp_kind in GLOBAL_FILES:
            if loaded_files_out is not None:
                loaded_files_out.append(rel_path)
            doc = DataLoader._read_json(source, rel_path, exp_kind, errors)
            if doc is not None:
                raw_docs[rel_path] = doc

        conv_raw = raw_docs.get("rules/conventions.json", {"gameSecToWorldSec": 60, "worldStepSec": 1, "cellKm": 1, "machKmh": 1200, "currency": "MUSD"})
        if conv_raw.get("worldStepSec", 1) != 1:
            errors.append(
                DataError(
                    "E_RANGE",
                    "rules/conventions.json",
                    "$.worldStepSec",
                    f"取值 {conv_raw.get('worldStepSec')} 超出范围 必须等于 1",
                )
            )
        cat.conventions = DataLoader.convert_units_tree(conv_raw, conv_raw, "rules/conventions.json", "$", cat.provisional_paths, errors)
        cat.rules["conventions"] = cat.conventions

        unit_seen: Dict[str, Tuple[str, str]] = {}
        weapon_raw_by_id: Dict[str, Tuple[Dict[str, Any], str, str]] = {}

        # Air defense units & weapons
        ad_doc = raw_docs.get("units/air_defense.json")
        if ad_doc is not None:
            conv_ad = DataLoader.convert_units_tree(ad_doc, cat.conventions, "units/air_defense.json", "$", cat.provisional_paths, errors)
            for ui, u in enumerate(conv_ad.get("units", [])):
                uid = u["id"]
                upath = f"$.units[{ui}]"
                if uid in unit_seen:
                    f0, p0 = unit_seen[uid]
                    errors.append(DataError("E_DUPLICATE_ID", "units/air_defense.json", f"{upath}.id", f'ID "{uid}" 重复（首次出现于 {f0} {p0}）'))
                else:
                    unit_seen[uid] = ("units/air_defense.json", f"{upath}.id")
                w_ids: List[str] = []
                for wi, w in enumerate(u.get("weapons", [])):
                    wpath = f"{upath}.weapons[{wi}]"
                    raw_w = ad_doc["units"][ui]["weapons"][wi]
                    if "rangeKm" not in raw_w:
                        errors.append(DataError("E_MISSING_FIELD", "units/air_defense.json", f"{wpath}.rangeKm", "缺少必填字段"))
                    elif not isinstance(raw_w["rangeKm"], (int, float)) or isinstance(raw_w["rangeKm"], bool):
                        errors.append(DataError("E_TYPE", "units/air_defense.json", f"{wpath}.rangeKm", "期望 number，实际 string"))
                    wid = w["id"]
                    w_ids.append(wid)
                    # Resolve targetsFrom gate
                    targets = list(w.get("targets", []))
                    for tf in w.get("targetsFrom", []) or []:
                        if DataLoader.is_gate_active(tf.get("from"), tf.get("until"), level_date, "units/air_defense.json", wpath):
                            if tf["tag"] not in targets:
                                targets.append(tf["tag"])
                    w["targets"] = targets
                    clean_raw = {rk: rv for rk, rv in raw_w.items() if rk not in IGNORED_FIELDS}
                    if wid in weapon_raw_by_id:
                        prev_raw, pf, pp = weapon_raw_by_id[wid]
                        if prev_raw != clean_raw:
                            errors.append(
                                DataError(
                                    "E_SHARED_WEAPON_MISMATCH",
                                    "units/air_defense.json",
                                    wpath,
                                    f'共享武器 "{wid}" 与 {pf} {pp} 的定义不一致',
                                )
                            )
                    else:
                        weapon_raw_by_id[wid] = (clean_raw, "units/air_defense.json", wpath)
                        cat.weapons[wid] = w
                u["weaponIds"] = w_ids
                cat.air_defense_units[uid] = u

        for rel_file, top_key, target_dict in (
            ("units/sensors.json", "sensors", cat.sensors),
            ("units/ew.json", "ewUnits", cat.ew_units),
            ("units/deception.json", "deceptionUnits", cat.deception_units),
        ):
            doc = raw_docs.get(rel_file)
            if doc is not None:
                conv_doc = DataLoader.convert_units_tree(doc, cat.conventions, rel_file, "$", cat.provisional_paths, errors)
                for idx, item in enumerate(conv_doc.get(top_key, [])):
                    uid = item["id"]
                    ipath = f"$.{top_key}[{idx}].id"
                    if uid in unit_seen:
                        f0, p0 = unit_seen[uid]
                        errors.append(DataError("E_DUPLICATE_ID", rel_file, ipath, f'ID "{uid}" 重复（首次出现于 {f0} {p0}）'))
                    else:
                        unit_seen[uid] = (rel_file, ipath)
                    target_dict[uid] = item

        enemy_seen: Dict[str, Tuple[str, str]] = {}
        mun_doc = raw_docs.get("enemies/munitions.json")
        if mun_doc is not None:
            conv_mun = DataLoader.convert_units_tree(mun_doc, cat.conventions, "enemies/munitions.json", "$", cat.provisional_paths, errors)
            for idx, m in enumerate(conv_mun.get("munitions", [])):
                mid = m["id"]
                mpath = f"$.munitions[{idx}]"
                if mid in enemy_seen:
                    f0, p0 = enemy_seen[mid]
                    errors.append(DataError("E_DUPLICATE_ID", "enemies/munitions.json", f"{mpath}.id", f'ID "{mid}" 重复（首次出现于 {f0} {p0}）'))
                else:
                    enemy_seen[mid] = ("enemies/munitions.json", f"{mpath}.id")
                acc = m.get("accuracy", "C")
                if "accuracyByPeriod" in m and m["accuracyByPeriod"]:
                    row = DataLoader.resolve_period_table(
                        m["accuracyByPeriod"], level_date, "enemies/munitions.json", f"{mpath}.accuracyByPeriod", errors, allow_fallback_none=True
                    )
                    if row is not None:
                        acc = row["tier"]
                m["accuracy"] = acc
                m["aiVisionActive"] = (
                    DataLoader.is_gate_active(m.get("aiVisionFrom"), None, level_date, "enemies/munitions.json", mpath)
                    if m.get("aiVisionFrom") is not None
                    else False
                )
                cat.munitions[mid] = m

        plat_doc = raw_docs.get("enemies/platforms.json")
        if plat_doc is not None:
            conv_plat = DataLoader.convert_units_tree(plat_doc, cat.conventions, "enemies/platforms.json", "$", cat.provisional_paths, errors)
            for idx, p in enumerate(conv_plat.get("platforms", [])):
                pid = p["id"]
                ppath = f"$.platforms[{idx}]"
                if pid in enemy_seen:
                    f0, p0 = enemy_seen[pid]
                    errors.append(DataError("E_DUPLICATE_ID", "enemies/platforms.json", f"{ppath}.id", f'ID "{pid}" 重复（首次出现于 {f0} {p0}）'))
                else:
                    enemy_seen[pid] = ("enemies/platforms.json", f"{ppath}.id")
                p["standoffActive"] = DataLoader.is_gate_active(p.get("standoffFrom"), None, level_date, "enemies/platforms.json", ppath)
                cat.platforms[pid] = p

        f_doc = raw_docs.get("support/fighters.json")
        if f_doc is not None:
            conv_f = DataLoader.convert_units_tree(f_doc, cat.conventions, "support/fighters.json", "$", cat.provisional_paths, errors)
            for idx, f in enumerate(conv_f.get("fighters", [])):
                cat.fighters[f["id"]] = f
                for w in f.get("weapons", []):
                    cat.fighter_weapons[w["id"]] = w

        s_doc = raw_docs.get("support/support.json")
        if s_doc is not None:
            conv_s = DataLoader.convert_units_tree(s_doc, cat.conventions, "support/support.json", "$", cat.provisional_paths, errors)
            for item in conv_s.get("support", []):
                cat.support[item["id"]] = item

        # Rules files 10..26
        for rel_path, exp_kind in GLOBAL_FILES[9:]:
            doc = raw_docs.get(rel_path)
            if doc is None or exp_kind is None:
                continue
            conv_r = DataLoader.convert_units_tree(doc, cat.conventions, rel_path, "$", cat.provisional_paths, errors)
            if exp_kind == "intercept":
                resolved_classes: Dict[str, Dict[str, float]] = {}
                for cls_name, tag_map in conv_r.get("classes", {}).items():
                    resolved_tags: Dict[str, float] = {}
                    for tag_name, pval in tag_map.items():
                        if tag_name in IGNORED_FIELDS:
                            continue
                        rv = DataLoader.resolve_period_value(
                            pval,
                            level_date,
                            rel_path,
                            f"$.classes.{cls_name}.{tag_name}",
                            errors,
                            allow_future_unlock=True,
                        )
                        if rv is not None:
                            resolved_tags[tag_name] = rv
                    resolved_classes[cls_name] = resolved_tags
                conv_r["classes"] = resolved_classes
                for mod_name, mod_obj in conv_r.get("modifiers", {}).items():
                    if isinstance(mod_obj, dict):
                        mod_obj["active"] = DataLoader.is_gate_active(
                            mod_obj.get("from"), mod_obj.get("until"), level_date, rel_path, f"$.modifiers.{mod_name}"
                        )
            elif exp_kind == "ew":
                if "effectivenessByPeriod" in conv_r:
                    row = DataLoader.resolve_period_table(
                        conv_r["effectivenessByPeriod"], level_date, rel_path, "$.effectivenessByPeriod", errors
                    )
                    conv_r["effectiveness"] = row or {"nav": 1.0, "counterUas": 1.0}
            elif exp_kind == "economy":
                for ev in conv_r.get("historicalEvents", []):
                    ev["active"] = DataLoader.is_gate_active(ev.get("from"), ev.get("until"), level_date, rel_path, "$.historicalEvents")
            cat.rules[exp_kind] = conv_r

        if errors_out is None and errors:
            raise DataLoadException(errors)
        return cat

    @staticmethod
    def load_level(source: IDataSource, level_id: str, night_index: Optional[int] = None) -> LevelData:
        errors: List[DataError] = []
        loaded_files: List[str] = []

        level_rel = f"levels/{level_id}/level.json"
        meta_raw = DataLoader._read_json(source, level_rel, None, errors)
        resolved_date = "2022-11-15"
        if meta_raw is not None and "dateRange" in meta_raw:
            resolved_date = meta_raw["dateRange"].get("from", resolved_date)

        # Pre-read waves.json for per-night date if night_index is specified (00_core.md §1.1 / §1.4)
        waves_rel = f"levels/{level_id}/waves.json"
        if night_index is not None and source.exists(waves_rel):
            try:
                w_pre = json.loads(source.read_bytes(waves_rel).decode("utf-8"))
                for n_obj in w_pre.get("nights", []):
                    if n_obj.get("night") == night_index and n_obj.get("date"):
                        resolved_date = n_obj["date"]
                        break
            except Exception:
                pass

        cat = DataLoader.load_catalog(source, resolved_date, errors_out=errors, loaded_files_out=loaded_files)
        provisional_paths = list(cat.provisional_paths)

        level_docs: Dict[str, Any] = {}
        for sub_path, exp_kind in LEVEL_JSON_FILES:
            rel = f"levels/{level_id}/{sub_path}"
            loaded_files.append(rel)
            if sub_path == "level.json":
                doc = meta_raw
            else:
                doc = DataLoader._read_json(source, rel, exp_kind, errors)
            if doc is not None:
                level_docs[sub_path] = DataLoader.convert_units_tree(doc, cat.conventions, rel, "$", provisional_paths, errors)

        meta = level_docs.get("level.json", {})
        waves = level_docs.get("waves.json", {"entryPoints": [], "nights": []})
        intel = level_docs.get("intel.json", {"nights": []})
        story_events = level_docs.get("events.json", {"events": []})
        layers = level_docs.get("map/layers.json", {})
        structures_doc = level_docs.get("map/structures.json", {"structures": []})
        structures = structures_doc.get("structures", [])
        grid = level_docs.get("map/grid.json", {"nodes": [], "links": []})
        deploy = level_docs.get("map/deploy.json", {"zones": [], "forbidden": [], "alternatePositions": []})

        # Heightmap PNG
        hm_info = meta.get("map", {}).get("heightmap", {"file": "map/heightmap.png", "metersPerPixel": 100.0, "minElevationM": 0.0, "maxElevationM": 200.0})
        hm_rel = f"levels/{level_id}/{hm_info.get('file', 'map/heightmap.png')}"
        loaded_files.append(hm_rel)
        heightmap = Heightmap(2, 2, 100.0, 0.0, 0.0, [0.0, 0.0, 0.0, 0.0])
        if source.exists(hm_rel):
            try:
                heightmap = Png16Decoder.decode(
                    source.read_bytes(hm_rel),
                    float(hm_info.get("metersPerPixel", 100.0)),
                    float(hm_info.get("minElevationM", 0.0)),
                    float(hm_info.get("maxElevationM", 200.0)),
                    hm_rel,
                )
                map_w = float(meta.get("map", {}).get("widthM", heightmap.width_px * heightmap.meters_per_pixel))
                map_h = float(meta.get("map", {}).get("heightM", heightmap.height_px * heightmap.meters_per_pixel))
                mpp = heightmap.meters_per_pixel
                if abs(heightmap.width_px * mpp - map_w) > mpp or abs(heightmap.height_px * mpp - map_h) > mpp:
                    errors.append(DataError("E_RANGE", hm_rel, "$", f"高程图尺寸 {heightmap.width_px}x{heightmap.height_px} 与地图尺寸 {map_w}x{map_h} 不一致"))
            except SimError as exc:
                errors.append(DataError(exc.code, exc.file_path or hm_rel, exc.json_path or "$", exc.message))
        else:
            errors.append(DataError("E_FILE_NOT_FOUND", hm_rel, "$", "文件不存在"))

        # Cross-reference checks (00_core.md §1.2 #15, #18)
        DataLoader._validate_cross_refs(level_id, meta, waves, intel, story_events, structures, grid, cat, errors)

        if errors:
            raise DataLoadException(errors)

        data_hash = DataLoader.compute_data_hash(source, loaded_files)
        urban_polys = [u.get("polygon", []) for u in layers.get("urban", [])]
        entry_by_id = {ep["id"]: ep for ep in waves.get("entryPoints", [])}

        return LevelData(
            id=meta.get("id", level_id),
            date=resolved_date,
            resolved_night_index=night_index,
            meta=meta,
            waves=waves,
            intel=intel,
            story_events=story_events,
            layers=layers,
            structures=structures,
            grid=grid,
            deploy=deploy,
            heightmap=heightmap,
            catalog=cat,
            data_hash=data_hash,
            loaded_files=loaded_files,
            provisional_paths=provisional_paths,
            urban_polygons=urban_polys,
            entry_points_by_id=entry_by_id,
        )

    @staticmethod
    def _validate_cross_refs(
        level_id: str,
        meta: Dict[str, Any],
        waves: Dict[str, Any],
        intel: Dict[str, Any],
        story_events: Dict[str, Any],
        structures: List[Dict[str, Any]],
        grid: Dict[str, Any],
        cat: GameCatalog,
        errors: List[DataError],
    ) -> None:
        all_units = set(cat.air_defense_units) | set(cat.sensors) | set(cat.ew_units) | set(cat.deception_units)
        all_enemies = set(cat.munitions) | set(cat.platforms)
        struct_ids = {s["id"] for s in structures}
        grid_ids = {n["id"] for n in grid.get("nodes", [])}
        entry_ids = {ep["id"] for ep in waves.get("entryPoints", [])}
        wave_ids: Set[str] = set()

        w_file = f"levels/{level_id}/waves.json"
        for ni, n_obj in enumerate(waves.get("nights", [])):
            if "date" in n_obj and n_obj["date"] and "dateRange" in meta:
                nd = DataLoader._ym_tuple(n_obj["date"], w_file, f"$.nights[{ni}].date")
                d_from = DataLoader._ym_tuple(meta["dateRange"]["from"], w_file, "$")
                d_to = DataLoader._ym_tuple(meta["dateRange"]["to"], w_file, "$")
                if not (d_from <= nd <= d_to or (meta["dateRange"]["from"] <= n_obj["date"] <= meta["dateRange"]["to"])):
                    errors.append(DataError("E_RANGE", w_file, f"$.nights[{ni}].date", f"取值 {n_obj['date']} 超出范围"))
                elif not (meta["dateRange"]["from"] <= n_obj["date"] <= meta["dateRange"]["to"]):
                    errors.append(DataError("E_RANGE", w_file, f"$.nights[{ni}].date", f"取值 {n_obj['date']} 超出范围"))
            for wi, w_obj in enumerate(n_obj.get("waves", [])):
                wave_ids.add(w_obj["id"])
                for gi, g_obj in enumerate(w_obj.get("groups", [])):
                    gpath = f"$.nights[{ni}].waves[{wi}].groups[{gi}]"
                    en_id = g_obj.get("enemy")
                    if en_id not in all_enemies:
                        errors.append(DataError("E_UNKNOWN_REF", w_file, f"{gpath}.enemy", f'引用的 敌方单位 "{en_id}" 不存在'))
                    ep_id = g_obj.get("entry")
                    if ep_id not in entry_ids:
                        errors.append(DataError("E_UNKNOWN_REF", w_file, f"{gpath}.entry", f'引用的 进入点 "{ep_id}" 不存在'))
                    tgt = g_obj.get("target", {})
                    if "structure" in tgt and tgt["structure"] is not None and tgt["structure"] not in struct_ids:
                        errors.append(DataError("E_UNKNOWN_REF", w_file, f"{gpath}.target.structure", f'引用的 保护目标 "{tgt["structure"]}" 不存在'))

        l_file = f"levels/{level_id}/level.json"
        for ai, au in enumerate(meta.get("availableUnits", [])):
            if au["unit"] not in all_units:
                errors.append(DataError("E_UNKNOWN_REF", l_file, f"$.availableUnits[{ai}].unit", f'引用的 单位 "{au["unit"]}" 不存在'))
        for qi, aq in enumerate(meta.get("ammoQuota", []) or []):
            if aq["weapon"] not in cat.weapons:
                errors.append(DataError("E_UNKNOWN_REF", l_file, f"$.ammoQuota[{qi}].weapon", f'引用的 武器 "{aq["weapon"]}" 不存在'))

        s_file = f"levels/{level_id}/map/structures.json"
        if grid_ids:
            for si, st in enumerate(structures):
                gn = st.get("gridNode")
                if gn is not None and gn not in grid_ids:
                    errors.append(DataError("E_UNKNOWN_REF", s_file, f"$.structures[{si}].gridNode", f'引用的 电网节点 "{gn}" 不存在'))
        g_file = f"levels/{level_id}/map/grid.json"
        if grid_ids:
            for li, lk in enumerate(grid.get("links", [])):
                if lk.get("from") not in grid_ids:
                    errors.append(DataError("E_UNKNOWN_REF", g_file, f"$.links[{li}].from", f'引用的 电网节点 "{lk.get("from")}" 不存在'))
                if lk.get("to") not in grid_ids:
                    errors.append(DataError("E_UNKNOWN_REF", g_file, f"$.links[{li}].to", f'引用的 电网节点 "{lk.get("to")}" 不存在'))

        i_file = f"levels/{level_id}/intel.json"
        for ni, n_obj in enumerate(intel.get("nights", [])):
            for ii, item in enumerate(n_obj.get("items", [])):
                rw = item.get("relatedWave")
                if rw is not None and rw not in wave_ids:
                    errors.append(DataError("E_UNKNOWN_REF", i_file, f"$.nights[{ni}].items[{ii}].relatedWave", f'引用的 波次 "{rw}" 不存在'))
