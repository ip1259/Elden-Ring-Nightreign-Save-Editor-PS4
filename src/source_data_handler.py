import pandas as pd
import pathlib
import functools
from typing import Optional, Union, Literal
import threading
import logging

from globals import (COLOR_MAP, LANGUAGE_MAP, CHARACTER_NAME_ID,
                     CHARACTER_NAMES, RELIC_GROUPS, get_system_language)


logger = logging.getLogger(__name__)


def df_filter_zero_chanceWeight(effects: pd.DataFrame) -> pd.DataFrame:
    """
    Filter effects DataFrame to include only those with non-zero FINAL chanceWeight.
    chanceWeight_dlc explains from Smithbox(unpacking tool):
    The DLC new Weighting to apply during the roll.
    -1 will use base roll weight(chanceWeight).

    Args:
        effects (pd.DataFrame): DataFrame import from AttachEffectTableParam.csv .\n
            Can be filtered before calling this function,\n
            but must have 'chanceWeight' and 'chanceWeight_dlc' columns.

    Returns:
        DataFrame:
            Filtered DataFrame with effects that have non-zero chanceWeight
    """
    _effs = effects.copy()
    _effs = _effs[(_effs["chanceWeight_dlc"] > 0) |
                  ((_effs["chanceWeight"] != 0) & (_effs["chanceWeight_dlc"] == -1))]
    return _effs


class AttachEffect:
    def __init__(self, effect_df: pd.DataFrame, name_df: pd.DataFrame, effect_id: int):
        self._data_frame = effect_df[effect_df.index == effect_id]
        self._is_empty_id = effect_id == 0xffffffff
        self._is_unknown = self._data_frame.empty and not self._is_empty_id
        self._name_df = name_df
        self.id = effect_id

    @property
    def name(self):
        if self._is_empty_id:
            return "Empty"
        elif self._is_unknown:
            return "Unknown"
        else:
            try:
                row = self._name_df[self._name_df["id"] == self.text_id]
                if not row.empty:
                    text = row["text"].values[0]
                    text = " ".join(text.split("\n"))
                    return text
                return "Unknown"
            except Exception:
                return "Unknown"

    @property
    def conflict_id(self):
        if self._is_empty_id or self._is_unknown:
            return -1
        return self._data_frame["compatibilityId"].values[0]

    @property
    def text_id(self):
        if self._is_empty_id or self._is_unknown:
            return -1
        return self._data_frame["attachTextId"].values[0]

    @property
    def sort_id(self):
        if self._is_empty_id or self._is_unknown:
            return float('inf')
        return self._data_frame["overrideEffectId"].values[0]

    def __repr__(self):
        return f"AttachEffect(id={self.id}, name='{self.name}', conflict_id={self.conflict_id}, text_id={self.text_id}, is_empty_id={self._is_empty_id}, is_unknown={self._is_unknown}, sort_id={self.sort_id})"

    def __str__(self):
        return f"{self.id}:{self.name}"


class Relic:
    def __init__(self, relic_df: pd.DataFrame, name_df: pd.DataFrame, relic_id: int):
        self._relic_df = relic_df[relic_df.index == relic_id]
        self._name_df = name_df
        self._is_empty_id = relic_id == 0x00000000
        self._is_unknown = self._relic_df.empty and not self._is_empty_id
        self.id = relic_id

    def is_deep(self):
        if self._is_empty_id or self._is_unknown:
            return False
        return self._relic_df["isDeepRelic"].values[0] == 1

    def is_salable(self):
        if self._is_empty_id or self._is_unknown:
            return False
        return self._relic_df["isSalable"].values[0] == 1

    @property
    def name(self):
        if self._is_empty_id:
            return "Empty"
        elif self._is_unknown:
            return "Unknown"
        else:
            try:
                row = self._name_df[self._name_df["id"] == self.id]
                if not row.empty:
                    return row["text"].values[0]
                return "Unknown"
            except Exception:
                return "Unknown"

    @property
    def color(self):
        if self._is_empty_id:
            return "Red"
        elif self._is_unknown:
            return "Red"
        else:
            try:
                color_id = self._relic_df["relicColor"].values[0]
                color_map = {
                    0: "Red",
                    1: "Blue",
                    2: "Yellow",
                    3: "Green",
                    4: "White"
                }
                return color_map[color_id]
            except Exception:
                return "Red"

    @property
    def color_id(self):
        if self._is_empty_id:
            return 0
        elif self._is_unknown:
            return 0
        else:
            try:
                color_id = self._relic_df["relicColor"].values[0]
                return color_id
            except Exception:
                return 0

    @property
    def effect_slots(self):
        if self._is_empty_id or self._is_unknown:
            return [-1, -1, -1, -1, -1, -1]
        try:
            slots = [
                int(self._relic_df["attachEffectTableId_1"].values[0]),
                int(self._relic_df["attachEffectTableId_2"].values[0]),
                int(self._relic_df["attachEffectTableId_3"].values[0]),
                int(self._relic_df["attachEffectTableId_curse1"].values[0]),
                int(self._relic_df["attachEffectTableId_curse2"].values[0]),
                int(self._relic_df["attachEffectTableId_curse3"].values[0])
            ]
            return slots
        except Exception:
            return [-1, -1, -1, -1, -1, -1]

    def __repr__(self):
        return f"Relic(id={self.id}, name='{self.name}', color='{self.color}', is_empty_id={self._is_empty_id}, is_unknown={self._is_unknown}, effect_slots={self.effect_slots})"

    def __str__(self):
        return f"{self.id}:{self.name}"


class Vessel:
    def __init__(self, df: pd.DataFrame, name_df: pd.DataFrame, vessel_id: int, npc_name_df: pd.DataFrame):
        self._df = df[df["ID"] == vessel_id]
        self._name_df = name_df
        self._npc_name_df = npc_name_df
        self.is_unknown = self._df.empty
        self.id = vessel_id

    @property
    def name(self):
        if self.is_unknown:
            return "Unknown"
        else:
            try:
                goods_id = self._df["goodsId"].values[0]
                row = self._name_df[self._name_df["id"] == goods_id]
                if not row.empty:
                    return row["text"].values[0]
                return "Unknown"
            except Exception:
                return "Unknown"

    @property
    def hero_type(self):
        if self.is_unknown:
            return -1
        return self._df["heroType"].values[0]

    @property
    def goods_id(self):
        if self.is_unknown:
            return -1
        return self._df["goodsId"].values[0]

    @property
    def hero_name(self):
        if self.is_unknown:
            return "Unknown"
        else:
            try:
                hero_index = self._df["heroType"].values[0]-1
                if hero_index == 10:
                    return "ALL"
                hero_id = CHARACTER_NAME_ID[hero_index]
                row = self._npc_name_df[self._npc_name_df["id"] == hero_id]
                if not row.empty:
                    return row["text"].values[0]
            except Exception:
                return "Unknown"

    @property
    def unlock_flag(self):
        if self.is_unknown:
            return -1
        return self._df["unlockFlag"].values[0]

    @property
    def relic_slots(self):
        if self.is_unknown:
            return (-1, -1, -1, -1, -1, -1)
        try:
            slots = (
                int(self._df["relicSlot1"].values[0]),
                int(self._df["relicSlot2"].values[0]),
                int(self._df["relicSlot3"].values[0]),
                int(self._df["deepRelicSlot1"].values[0]),
                int(self._df["deepRelicSlot2"].values[0]),
                int(self._df["deepRelicSlot3"].values[0])
            )
            return slots
        except Exception:
            return (-1, -1, -1, -1, -1, -1)

    @property
    def slot_colors(self):
        if self.is_unknown:
            return ["Unknown", "Unknown", "Unknown", "Unknown", "Unknown", "Unknown"]
        try:
            slots = [
                COLOR_MAP[int(self._df["relicSlot1"].values[0])],
                COLOR_MAP[int(self._df["relicSlot2"].values[0])],
                COLOR_MAP[int(self._df["relicSlot3"].values[0])],
                COLOR_MAP[int(self._df["deepRelicSlot1"].values[0])],
                COLOR_MAP[int(self._df["deepRelicSlot2"].values[0])],
                COLOR_MAP[int(self._df["deepRelicSlot3"].values[0])]
            ]
            return slots
        except Exception:
            return ["Unknown", "Unknown", "Unknown", "Unknown", "Unknown", "Unknown"]

    def __repr__(self):
        return f"Vessel(id={self.id}, name='{self.name}', hero_type={self.hero_type}, goods_id={self.goods_id}, hero_name='{self.hero_name}', unlock_flag={self.unlock_flag}, relic_slots={self.relic_slots})"

    def __str__(self):
        return f"{self.id}:{self.name}"


class SourceDataHandler:
    _instance = None
    _initialized = False
    _lock = threading.Lock()

    WORKING_DIR = pathlib.Path(__file__).parent.resolve()
    PARAM_DIR = pathlib.Path(WORKING_DIR / "Resources/Param")
    TEXT_DIR = pathlib.Path(WORKING_DIR / "Resources/Text")
    RELIC_TEXT_FILE_NAME = ["AntiqueName.fmg.xml", "AntiqueName_dlc01.fmg.xml"]
    EFFECT_NAME_FILE_NAMES = [
        "AttachEffectName.fmg.xml",
        "AttachEffectName_dlc01.fmg.xml",
    ]
    NPC_NAME_FILE_NAMES = [
        "NpcName.fmg.xml",
        "NpcName_dlc01.fmg.xml",
    ]
    GOODS_NAME_FILE_NAMES = [
        "GoodsName.fmg.xml",
        "GoodsName_dlc01.fmg.xml",
    ]
    character_names = CHARACTER_NAMES

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            logger.info("Creating SourceDataHandler instance...")
            logger.info("Trying to get lock...")
            with cls._lock:
                logger.info("Got lock! Checking instance again...")
                if cls._instance is None:
                    logger.info("Creating new instance...")
                    cls._instance = super(SourceDataHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self, language: str = get_system_language()):
        if self._initialized:
            logger.debug("SourceDataHandler already initialized. Returning...")
            return
        logger.info("Initializing SourceDataHandler...")
        logger.info("Trying to get lock...")
        with self._lock:
            logger.info("Got lock! Checking is instance initialized again...")
            if not self._initialized:
                logger.info("Initializing SourceDataHandler...")
                self._initialized = True
                logger.info("Loading Effects Parameter Files...")
                self._effect_params = \
                    pd.read_csv(self.PARAM_DIR / "AttachEffectParam.csv")
                self._effect_params: pd.DataFrame = self._effect_params[
                    ["ID", "compatibilityId", "attachTextId", "overrideEffectId"]
                ]
                self._effect_params.set_index("ID", inplace=True)

                logger.info("Loading AttachEffectTable Parameter Files...")
                self.effect_table = \
                    pd.read_csv(self.PARAM_DIR / "AttachEffectTableParam.csv")
                self.effect_table: pd.DataFrame = \
                    self.effect_table[["ID", "attachEffectId", "chanceWeight", "chanceWeight_dlc"]]

                logger.info("Loading Antique(Relic) Parameter Files...")
                self._relic_table = \
                    pd.read_csv(self.PARAM_DIR / "EquipParamAntique.csv")
                self._relic_table: pd.DataFrame = self._relic_table[
                    [
                        "ID",
                        "relicColor",
                        "isDeepRelic",
                        "isSalable",
                        "attachEffectTableId_1",
                        "attachEffectTableId_2",
                        "attachEffectTableId_3",
                        "attachEffectTableId_curse1",
                        "attachEffectTableId_curse2",
                        "attachEffectTableId_curse3",
                    ]
                ]
                self._relic_table.set_index("ID", inplace=True)

                logger.info("Loading AntiqueStand Parameter Files...")
                self.antique_stand_param: pd.DataFrame = \
                    pd.read_csv(self.PARAM_DIR / "AntiqueStandParam.csv")

                self.relic_name: Optional[pd.DataFrame] = None
                self.effect_name: Optional[pd.DataFrame] = None
                self.npc_name: Optional[pd.DataFrame] = None
                # Track which relic IDs are from 1.03 patch (Scene relics)
                self._scene_relic_ids: set = set()
                self.vessel_names: Optional[pd.DataFrame] = None
                self._load_text(language)
                self.effects: dict[int, AttachEffect] = {}
                self._set_effects()
                self.relics: dict[int, Relic] = {}
                self._set_relics()
                self.vessels: dict[int, Vessel] = {}
                self._set_vessels()

    def _load_text(self, language: str = "en_US"):
        logger.info(f"Loading text for language: {language}")
        support_languages = LANGUAGE_MAP.keys()
        _lng = language
        if language not in support_languages:
            logger.warning(f"{language} is not supported. Falling back to default 'en_US'.")
            _lng = "en_US"
        # Deal with Relic text
        # Read all Relic xml from language subfolder
        # Track which IDs come from _dlc01 file (1.03 patch / Scene relics)
        _relic_names: Optional[pd.DataFrame] = None
        self._scene_relic_ids = set()
        logger.info("Loading Relic text...")
        for file_name in SourceDataHandler.RELIC_TEXT_FILE_NAME:
            _df = pd.read_xml(
                SourceDataHandler.TEXT_DIR / _lng / file_name,
                xpath="/fmg/entries/text"
            )
            # Track IDs from dlc01 file as Scene relics (1.03 patch)
            if "_dlc01" in file_name:
                valid_ids = _df[_df['text'] != '%null%']['id'].tolist()
                self._scene_relic_ids.update(valid_ids)
            if _relic_names is None:
                _relic_names = _df
            else:
                _relic_names = pd.concat([_relic_names, _df])

        # Deal with Effect text
        # Read all Effect xml from language subfolder
        logger.info("Loading Effect text...")
        _effect_names: Optional[pd.DataFrame] = None
        for file_name in SourceDataHandler.EFFECT_NAME_FILE_NAMES:
            _df = pd.read_xml(
                SourceDataHandler.TEXT_DIR / _lng / file_name,
                xpath="/fmg/entries/text"
            )
            if _effect_names is None:
                _effect_names = _df
            else:
                _effect_names = pd.concat([_effect_names, _df])

        # Deal with NPC text
        # Read all NPC xml from language subfolder
        logger.info("Loading NPC text...")
        _npc_names: Optional[pd.DataFrame] = None
        for file_name in SourceDataHandler.NPC_NAME_FILE_NAMES:
            _df = pd.read_xml(
                SourceDataHandler.TEXT_DIR / _lng / file_name,
                xpath="/fmg/entries/text"
            )
            if _npc_names is None:
                _npc_names = _df
            else:
                _npc_names = pd.concat([_npc_names, _df])

        self.character_names.clear()
        for id in CHARACTER_NAME_ID:
            _name = _npc_names[_npc_names["id"] == id]["text"].to_list()[0]
            self.character_names.append(_name)

        # Deal with Goods Names
        # Read all Goods xml from language subfolder
        logger.info("Loading Goods text...")
        _goods_names: Optional[pd.DataFrame] = None
        for file_name in SourceDataHandler.GOODS_NAME_FILE_NAMES:
            _df = pd.read_xml(
                SourceDataHandler.TEXT_DIR / _lng / file_name,
                xpath="/fmg/entries/text"
            )
            if _goods_names is None:
                _goods_names = _df
            else:
                _goods_names = pd.concat([_goods_names, _df])

        _vessel_names = _goods_names[(9600 <= _goods_names["id"]) &
                                     (_goods_names["id"] <= 9956) &
                                     (_goods_names["text"] != "%null%")]
        logger.info("Setting Vessel Names...")
        if self.vessel_names is None:
            self.vessel_names = _vessel_names
        else:
            _vessel_names.set_index('id')
            self.vessel_names.set_index('id')
            self.vessel_names.update(_vessel_names)
            self.vessel_names.reset_index()
        logger.info("Setting NPC Names...")
        if self.npc_name is None:
            self.npc_name = _npc_names
        else:
            self.npc_name.set_index('id')
            _npc_names.set_index('id')
            self.npc_name.update(_npc_names)
            self.npc_name.reset_index()
        logger.info("Setting Relic Names...")
        if self.relic_name is None:
            self.relic_name = _relic_names
        else:
            self.relic_name.set_index('id')
            _relic_names.set_index('id')
            self.relic_name.update(_relic_names)
            self.relic_name.reset_index()
        logger.info("Setting Effect Names...")
        if self.effect_name is None:
            self.effect_name = _effect_names
        else:
            self.effect_name.set_index('id')
            _effect_names.set_index('id')
            self.effect_name.update(_effect_names)
            self.effect_name.reset_index()

    def reload_text(self, language: str = "en_US"):
        logger.info(f"Reloading text for language: {language}")
        try:
            self._load_text(language=language)
            return True
        except FileNotFoundError:
            self._load_text()
            return False
        except KeyError:
            self._load_text()
            return False

    def _set_effects(self):
        logger.info("Setting Effects...")
        logger.info("Setting 'Empty Effect' Data...")
        # Empty effect first
        self.effects[0xffffffff] = AttachEffect(self._effect_params,
                                                self.effect_name,
                                                0xffffffff)
        # Iterate through the entire effect param DataFrame
        logger.info("Setting All Effects Data...")
        for index, row in self._effect_params.iterrows():
            effect_id = index
            self.effects[effect_id] = AttachEffect(self._effect_params,
                                                   self.effect_name,
                                                   effect_id)

    def _set_relics(self):
        logger.info("Setting Relic Data...")
        for index, row in self._relic_table.iterrows():
            relic_id = index
            self.relics[relic_id] = Relic(self._relic_table,
                                          self.relic_name,
                                          relic_id)

    def _set_vessels(self):
        logger.info("Setting Vessel Data...")
        for index, row in self.antique_stand_param.iterrows():
            vessel_id = row["ID"]
            self.vessels[vessel_id] = Vessel(self.antique_stand_param,
                                             self.vessel_names,
                                             vessel_id,
                                             self.npc_name)

    def get_support_languages_name(self):
        return LANGUAGE_MAP.values()

    def get_support_languages_code(self):
        return LANGUAGE_MAP.keys()

    def get_support_languages(self):
        return LANGUAGE_MAP

    def is_scene_relic(self, relic_id: int) -> bool:
        """Check if a relic is a Scene relic (added in patch 1.03).

        Scene relics have different effect pools than original relics,
        which is why certain effects can only be found on Scene relics
        and vice versa.

        Returns:
            True if the relic is a Scene relic (1.03+), False otherwise
        """
        return relic_id in self._scene_relic_ids

    def get_relic_type_info(self, relic_id: int) -> tuple:
        """Get relic type information for display purposes.

        Returns:
            Tuple of (type_name, description, color_hex)
            - type_name: "Scene" or "Original"
            - description: Brief explanation of what this means
            - color_hex: Color for display
        """
        if self.is_scene_relic(relic_id):
            return (
                "Scene Relic (1.03+)",
                "Has unique effect pools not found on original relics",
                "#9966CC"  # Purple for Scene relics
            )
        else:
            return (
                "Original Relic",
                "Has effect pools from base game release",
                "#666666"  # Gray for original relics
            )

    def get_pool_effects(self, pool_id: int):
        logger.debug(f"Getting effects for pool {pool_id}")
        if pool_id == -1:
            return []
        _effects = self.effect_table[self.effect_table["ID"] == pool_id]
        _effects = _effects["attachEffectId"].values.tolist()
        return _effects

    @functools.cache
    def _get_rollable_effects_wrapped(
        self, pool_type: Literal["normal", "deep", "curse"] = "normal"
    ) -> list[int]:
        pools: set[int] = set()
        relics = self._relic_table[
            self._relic_table.index.to_series().isin(self.get_safe_relic_ids())
        ]
        match pool_type:
            case "normal":
                relics = relics[relics["isDeepRelic"] == 0]
                pools |= set(relics["attachEffectTableId_1"].values.tolist())
                pools |= set(relics["attachEffectTableId_2"].values.tolist())
                pools |= set(relics["attachEffectTableId_3"].values.tolist())
            case "deep":
                relics = relics[relics["isDeepRelic"] > 0]
                pools |= set(relics["attachEffectTableId_1"].values.tolist())
                pools |= set(relics["attachEffectTableId_2"].values.tolist())
                pools |= set(relics["attachEffectTableId_3"].values.tolist())
            case "curse":
                pools |= set(relics["attachEffectTableId_curse1"].values.tolist())
                pools |= set(relics["attachEffectTableId_curse2"].values.tolist())
                pools |= set(relics["attachEffectTableId_curse3"].values.tolist())
        effects = self.effect_table[self.effect_table["ID"].isin(pools)]
        effects = df_filter_zero_chanceWeight(effects)
        return effects["attachEffectId"].unique().tolist()

    def get_rollable_effects(
        self, pool_type: Literal["normal", "deep", "curse"] = "normal"
    ):
        """Get all effects that can roll (chanceWeight > 0) in a given pool type
        (normal, deep, or curse).
        """
        logger.debug(f"Getting rollable effects for {pool_type} pool")
        return self._get_rollable_effects_wrapped(pool_type)

    def get_pool_rollable_effects(self, pool_id: int):
        """Get effects that can actually roll in a pool (chanceWeight != 0).

        Effects with weight -65536 are disabled (cannot roll).
        Effects with weight 0 are class-specific effects that cannot naturally roll.
        Other weights (including other negative values) are valid rollable weights.

        For deep pools (2000000, 2100000, 2200000), returns effects that have
        rollable weight in ANY of the three deep pools, since the game appears
        to allow effects to roll on any deep relic if they're valid in any deep pool.
        """
        logger.debug(f"Getting rollable effects for pool {pool_id}")
        if pool_id == -1:
            return []

        # Deep pools are interchangeable - effect valid in any deep pool is valid for all
        deep_pools = {2000000, 2100000, 2200000}
        if pool_id in deep_pools:
            # Get effects with rollable weight in ANY deep pool
            _effects = self.effect_table[self.effect_table["ID"].isin(deep_pools)]
            _effects = df_filter_zero_chanceWeight(_effects)
            return _effects["attachEffectId"].unique().tolist()

        # For non-deep pools, check the specific pool
        _effects = self.effect_table[self.effect_table["ID"] == pool_id]
        # Filter out disabled (-65536) and zero-weight effects
        _effects = df_filter_zero_chanceWeight(_effects)
        return _effects["attachEffectId"].values.tolist()

    def get_pool_effects_strict(self, pool_id: int):
        """Get effects that can roll in a SPECIFIC pool (chanceWeight != 0).

        Unlike get_pool_rollable_effects(), this does NOT combine deep pools.
        Use this for strict validation to detect effects that are valid in some
        deep pool but not in the specific pool assigned to a relic.
        """
        logger.debug(f"Getting strict effects for pool {pool_id}")
        if pool_id == -1:
            return []
        _effects = self.effect_table[self.effect_table["ID"] == pool_id]
        _effects = df_filter_zero_chanceWeight(_effects)
        return _effects["attachEffectId"].values.tolist()

    def get_effect_pools(self, effect_id: int):
        """Get all pool IDs that contain a specific effect."""
        logger.debug(f"Getting pools for effect {effect_id}")
        _pools = self.effect_table[self.effect_table["attachEffectId"] == effect_id]
        return _pools["ID"].values.tolist()

    def get_effect_rollable_pools(self, effect_id: int):
        """Get all pool IDs where this effect can actually roll (chanceWeight != 0)."""
        logger.debug(f"Getting rollable pools for effect {effect_id}")
        _rows = self.effect_table[self.effect_table["attachEffectId"] == effect_id]
        # Filter out rows where chanceWeight is 0 (cannot roll)
        _rollable = df_filter_zero_chanceWeight(_rows)
        return _rollable["ID"].values.tolist()

    def is_deep_only_effect(self, effect_id: int):
        """Check if an effect only exists in deep relic pools (2000000, 2100000, 2200000)
        plus its own dedicated pool (effect_id == pool_id).
        These effects require curses when used on multi-effect relics."""
        logger.debug(f"Checking if effect {effect_id} is deep-only")
        if effect_id in [-1, 0, 4294967295]:
            return False
        pools = self.get_effect_pools(effect_id)
        deep_pools = {2000000, 2100000, 2200000}
        for pool in pools:
            # If pool is not a deep pool and not the effect's dedicated pool, it's not deep-only
            if pool not in deep_pools and pool != effect_id:
                return False
        return True

    def effect_needs_curse(self, effect_id: int) -> bool:
        """Check if an effect REQUIRES a curse.

        An effect needs a curse if it can ONLY roll from pool 2000000 (3-effect relics)
        and NOT from pools 2100000 or 2200000 (single-effect relics with no curse).

        We check rollable pools (weight != -65536) because an effect may be listed
        in a pool but with weight -65536 meaning it can't actually roll there.
        """
        logger.debug(f"Checking if effect {effect_id} needs a curse")
        if effect_id in [-1, 0, 4294967295]:
            return False

        # Get pools where this effect can actually roll
        pools = self.get_effect_rollable_pools(effect_id)

        # Pool 2000000 = 3-effect relics (always have curse slots)
        # Pools 2100000, 2200000 = single-effect relics (no curse slots)
        curse_required_pool = 2000000
        curse_free_pools = {2100000, 2200000}

        in_curse_required_pool = False
        in_curse_free_pool = False

        for pool in pools:
            if pool == effect_id:
                # Skip dedicated pool (effect's own pool)
                continue
            if pool == curse_required_pool:
                in_curse_required_pool = True
            elif pool in curse_free_pools:
                in_curse_free_pool = True

        # Effect needs curse only if it can roll from pool 2000000
        # AND cannot roll from any curse-free pool (2100000 or 2200000)
        return in_curse_required_pool and not in_curse_free_pool

    def get_adjusted_pool_sequence(self, relic_id: int,
                                   effects: list[int]):
        """
        Get adjusted pool sequence for a relic based on its effects.
        For each of the first three effects, check if it requires a curse.
        If it does, assign the next available curse pool ID.
        If it doesn't, assign -1.
        """
        logger.debug(f"Getting adjusted pool sequence for relic {relic_id}")
        effs = effects[:3]
        pool_ids = self.relics[relic_id].effect_slots
        curse_pools = pool_ids[3:]
        new_pool_ids = pool_ids[:3]
        for i in range(3):
            if self.effect_needs_curse(effs[i]):
                new_pool_ids.append(curse_pools.pop(0))
            else:
                new_pool_ids.append(-1)
        return new_pool_ids

    def get_relic_slot_count(self, relic_id: int) -> tuple[int, int]:
        logger.debug(f"Getting relic slot count for relic {relic_id}")
        pool_seq: list = self.relics[relic_id].effect_slots
        effect_slot = pool_seq[:3]
        curse_slot = pool_seq[3:]
        return 3-effect_slot.count(-1), 3-curse_slot.count(-1)

    def get_character_name(self, character_id: int):
        return self.npc_name[self.npc_name["id"] == character_id]["text"].values[0]

    def get_filtered_relics_df(self, color: Union[int, str] = None,
                               deep: Optional[bool] = None,
                               effect_slot: Optional[int] = None,
                               curse_slot: Optional[int] = None):
        """
        Get filtered relics DataFrame based on criteria.
        
        :param color: Color of the relic (e.g., 'Red', 'Blue')
            Suooprt both int (color ID) and str (color name).
        :type color: Union[int, str]
        :param deep: Whether to filter for deep relics (True), non-deep relics (False), or all (None).
        :type deep: Optional[bool]
        :param effect_slot: Number of effect slots to filter for.
        :type effect_slot: Optional[int]
        :param curse_slot: Number of curse slots to filter for.
        :type curse_slot: Optional[int]
        """
        logger.info(f"Getting filtered relics DataFrame with criteria: color={color}, deep={deep}, effect_slot={effect_slot}, curse_slot={curse_slot}")
        result_df: pd.DataFrame = self._relic_table.copy()
        result_df.reset_index(inplace=True)
        safe_range = self.get_safe_relic_ids()
        result_df = result_df[result_df["ID"].isin(safe_range)]
        if color is not None:
            color_id = 0
            if type(color) is str:
                color_id = COLOR_MAP.index(color)
            else:
                color_id = color
            result_df = result_df[result_df["relicColor"] == color_id]
        if deep is not None:
            if deep:
                result_df = result_df[result_df["ID"].apply(self.is_deep_relic)]
            else:
                result_df = result_df[~result_df["ID"].apply(self.is_deep_relic)]
        if effect_slot is not None:
            result_df = result_df[result_df["ID"].apply(
                lambda x: self.get_relic_slot_count(x)[0] == effect_slot)]
        if curse_slot is not None:
            result_df = result_df[result_df["ID"].apply(
                lambda x: self.get_relic_slot_count(x)[1] == curse_slot)]
        return result_df

    @staticmethod
    def get_safe_relic_ids():
        """
        Get a list of safe relic IDs from predefined RELIC_GROUPS.
        """
        range_names = ["store_102", "store_103", "reward_0",
                       "reward_1", "reward_2", "reward_3",
                       "reward_4", "reward_5", "reward_6", "reward_7",
                       "reward_8", "reward_9", "deep_102", "deep_103"]
        safe_relic_ids = []
        for group_name, group_range in RELIC_GROUPS.items():
            if group_name in range_names:
                safe_relic_ids.extend(range(group_range[0], group_range[1] + 1))
        return safe_relic_ids

    @staticmethod
    def is_deep_relic(relic_id: int):
        """
        Check if a relic ID belongs to deep relic groups.

        :param relic_id: Relic ID to check.
        :type relic_id: int
        """
        deep_range_1 = range(RELIC_GROUPS['deep_102'][0],
                             RELIC_GROUPS['deep_102'][1] + 1)
        deep_range_2 = range(RELIC_GROUPS['deep_103'][0],
                             RELIC_GROUPS['deep_103'][1] + 1)
        return relic_id in deep_range_1 or relic_id in deep_range_2


if __name__ == "__main__":
    source_data_handler = SourceDataHandler()
    t = source_data_handler.vessels[4003]
    print(repr(t))
    source_data_handler.reload_text("zh_TW")
    print(repr(t))
