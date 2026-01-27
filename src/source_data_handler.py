import pandas as pd
import pathlib
from typing import Optional, Union
import locale
import threading

from globals import COLOR_MAP, LANGUAGE_MAP, CHARACTER_NAME_ID, CHARACTER_NAMES, RELIC_GROUPS
from basic_class import AttachEffect, Relic, Vessel


def get_system_language():
    lang = None

    try:
        lang, _ = locale.getdefaultlocale()
    except Exception:
        return "en_US"

    if lang:
        normalized = locale.normalize(lang)
        clean_lang = normalized.split('.')[0]
        clean_lang = clean_lang.replace('-', '_')
        if clean_lang in LANGUAGE_MAP:
            return clean_lang
        else:
            return "en_US"
    return "en_US"


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
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SourceDataHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self, language: str = get_system_language()):
        if self._initialized:
            return
        with self._lock:
            self._initialized = True
            self._effect_params = \
                pd.read_csv(self.PARAM_DIR / "AttachEffectParam.csv")
            self._effect_params: pd.DataFrame = self._effect_params[
                ["ID", "compatibilityId", "attachTextId", "overrideEffectId"]
            ]
            self._effect_params.set_index("ID", inplace=True)

            self.effect_table = \
                pd.read_csv(self.PARAM_DIR / "AttachEffectTableParam.csv")
            self.effect_table: pd.DataFrame = \
                self.effect_table[["ID", "attachEffectId", "chanceWeight", "chanceWeight_dlc"]]

            self._relic_table = \
                pd.read_csv(self.PARAM_DIR / "EquipParamAntique.csv")
            self._relic_table: pd.DataFrame = self._relic_table[
                [
                    "ID",
                    "relicColor",
                    "isDeepRelic",
                    "attachEffectTableId_1",
                    "attachEffectTableId_2",
                    "attachEffectTableId_3",
                    "attachEffectTableId_curse1",
                    "attachEffectTableId_curse2",
                    "attachEffectTableId_curse3",
                ]
            ]
            self._relic_table.set_index("ID", inplace=True)

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
        support_languages = LANGUAGE_MAP.keys()
        _lng = language
        if language not in support_languages:
            _lng = "en_US"
        # Deal with Relic text
        # Read all Relic xml from language subfolder
        # Track which IDs come from _dlc01 file (1.03 patch / Scene relics)
        _relic_names: Optional[pd.DataFrame] = None
        self._scene_relic_ids = set()
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
        if self.vessel_names is None:
            self.vessel_names = _vessel_names
        else:
            _vessel_names.set_index('id')
            self.vessel_names.set_index('id')
            self.vessel_names.update(_vessel_names)
            self.vessel_names.reset_index()
        if self.npc_name is None:
            self.npc_name = _npc_names
        else:
            self.npc_name.set_index('id')
            _npc_names.set_index('id')
            self.npc_name.update(_npc_names)
            self.npc_name.reset_index()
        if self.relic_name is None:
            self.relic_name = _relic_names
        else:
            self.relic_name.set_index('id')
            _relic_names.set_index('id')
            self.relic_name.update(_relic_names)
            self.relic_name.reset_index()
        if self.effect_name is None:
            self.effect_name = _effect_names
        else:
            self.effect_name.set_index('id')
            _effect_names.set_index('id')
            self.effect_name.update(_effect_names)
            self.effect_name.reset_index()

    def reload_text(self, language: str = "en_US"):
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
        # Empty effect first
        self.effects[0xffffffff] = AttachEffect(self._effect_params,
                                                self.effect_name,
                                                0xffffffff)
        # Iterate through the entire effect param DataFrame
        for index, row in self._effect_params.iterrows():
            effect_id = index
            self.effects[effect_id] = AttachEffect(self._effect_params,
                                                   self.effect_name,
                                                   effect_id)

    def _set_relics(self):
        for index, row in self._relic_table.iterrows():
            relic_id = index
            self.relics[relic_id] = Relic(self._relic_table,
                                          self.relic_name,
                                          relic_id)

    def _set_vessels(self):
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

    def get_relic_origin_structure(self):
        if self.relic_name is None:
            self._load_text()
        _copy_df = self.relic_name.copy()
        _copy_df.set_index("id", inplace=True)
        _copy_df.rename(columns={"text": "name"}, inplace=True)
        _result = {}
        for index, row in self._relic_table.iterrows():
            try:
                _name_matches = \
                    _copy_df[_copy_df.index == index]["name"].values
                _color_matches = \
                    self._relic_table[self._relic_table.index == index][
                        "relicColor"].values
                first_name_val = \
                    _name_matches[0] if len(_name_matches) > 0 else "Unset"
                first_color_val = COLOR_MAP[int(_color_matches[0])] if len(_color_matches) > 0 else "Red"
                _result[str(index)] = {
                    "name": str(first_name_val),
                    "color": first_color_val,
                }
            except KeyError:
                _result[str(index)] = {"name": "Unset", "color": "Red"}
        return _result

    def cvrt_filtered_relic_origin_structure(self,
                                             relic_dataframe: pd.DataFrame):
        if self.relic_name is None:
            self._load_text()
        _copy_df = self.relic_name.copy()
        _copy_df.set_index("id", inplace=True)
        _copy_df.rename(columns={"text": "name"}, inplace=True)
        _result = {}
        for index, row in relic_dataframe.iterrows():
            try:
                _name_matches = \
                    _copy_df[_copy_df.index == index]["name"].values
                _color_matches = \
                    relic_dataframe[relic_dataframe.index == index][
                        "relicColor"].values
                first_name_val = \
                    _name_matches[0] if len(_name_matches) > 0 else "Unset"
                first_color_val = COLOR_MAP[int(_color_matches[0])] if len(_color_matches) > 0 else "Red"
                _result[str(index)] = {
                    "name": str(first_name_val),
                    "color": first_color_val,
                }
            except KeyError:
                _result[str(index)] = {"name": "Unset", "color": "Red"}
        return _result

    def get_effect_origin_structure(self):
        if self.effect_name is None:
            self._load_text()
        _copy_df = self.effect_name.copy()
        _copy_df.set_index("id", inplace=True)
        _reslut = {"4294967295": {"name": "Empty"}}
        for index, row in self._effect_params.iterrows():
            try:
                _attachTextId = self._effect_params.loc[index, "attachTextId"]
                matches = \
                    _copy_df[_copy_df.index == _attachTextId]["text"].values
                first_val = matches[0] if len(matches) > 0 else "Unknown"
                _reslut[str(index)] = {"name": str(first_val)}
            except KeyError:
                _reslut[str(index)] = {"name": "Unknown"}
        return _reslut

    def cvrt_filtered_effect_origin_structure(self,
                                              effect_dataframe: pd.DataFrame):
        if self.effect_name is None:
            self._load_text()
        _copy_df = self.effect_name.copy()
        _copy_df.set_index("id", inplace=True)
        _reslut = {}
        for index, row in effect_dataframe.iterrows():
            try:
                _attachTextId = effect_dataframe.loc[index, "attachTextId"]
                matches = \
                    _copy_df[_copy_df.index == _attachTextId]["text"].values
                first_val = matches[0] if len(matches) > 0 else "Unknown"
                _reslut[str(index)] = {"name": str(first_val)}
            except KeyError:
                _reslut[str(index)] = {"name": "Unknown"}
        if len(_reslut) == 0:
            _reslut = {"4294967295": {"name": "Empty"}}
        return _reslut

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
        if pool_id == -1:
            return []
        _effects = self.effect_table[self.effect_table["ID"] == pool_id]
        _effects = _effects["attachEffectId"].values.tolist()
        return _effects

    def get_pool_rollable_effects(self, pool_id: int):
        """Get effects that can actually roll in a pool (chanceWeight != 0).

        Effects with weight -65536 are disabled (cannot roll).
        Effects with weight 0 are class-specific effects that cannot naturally roll.
        Other weights (including other negative values) are valid rollable weights.

        For deep pools (2000000, 2100000, 2200000), returns effects that have
        rollable weight in ANY of the three deep pools, since the game appears
        to allow effects to roll on any deep relic if they're valid in any deep pool.
        """
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
        if pool_id == -1:
            return []
        _effects = self.effect_table[self.effect_table["ID"] == pool_id]
        _effects = df_filter_zero_chanceWeight(_effects)
        return _effects["attachEffectId"].values.tolist()

    def get_effect_pools(self, effect_id: int):
        """Get all pool IDs that contain a specific effect."""
        _pools = self.effect_table[self.effect_table["attachEffectId"] == effect_id]
        return _pools["ID"].values.tolist()

    def get_effect_rollable_pools(self, effect_id: int):
        """Get all pool IDs where this effect can actually roll (chanceWeight != 0)."""
        _rows = self.effect_table[self.effect_table["attachEffectId"] == effect_id]
        # Filter out rows where chanceWeight is 0 (cannot roll)
        _rollable = df_filter_zero_chanceWeight(_rows)
        return _rollable["ID"].values.tolist()

    def is_deep_only_effect(self, effect_id: int):
        """Check if an effect only exists in deep relic pools (2000000, 2100000, 2200000)
        plus its own dedicated pool (effect_id == pool_id).
        These effects require curses when used on multi-effect relics."""
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
