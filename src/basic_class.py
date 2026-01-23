import struct
from globals import ITEM_TYPE_WEAPON, ITEM_TYPE_ARMOR, ITEM_TYPE_RELIC, CHARACTER_NAME_ID, COLOR_MAP
import pandas as pd


class Item:
    BASE_SIZE = 8

    def __init__(self, gaitem_handle, item_id, effect_1, effect_2, effect_3,
                 durability, unk_1, sec_effect1, sec_effect2, sec_effect3,
                 unk_2, offset, extra=None, size=BASE_SIZE):
        self.gaitem_handle = gaitem_handle
        self.item_id = item_id
        self.effect_1 = effect_1
        self.effect_2 = effect_2
        self.effect_3 = effect_3
        self.durability = durability
        self.unk_1 = unk_1
        self.sec_effect1 = sec_effect1
        self.sec_effect2 = sec_effect2
        self.sec_effect3 = sec_effect3
        self.unk_2 = unk_2
        self.offset = offset
        self.size = size
        self.padding = extra or ()

    @classmethod
    def from_bytes(cls, data_type, offset=0):
        data_len = len(data_type)

        # Check if we have enough data for the base read
        if offset + cls.BASE_SIZE > data_len:
            # Return empty item if not enough data
            return cls(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, offset, size=cls.BASE_SIZE)

        gaitem_handle, item_id = struct.unpack_from("<II", data_type, offset)
        type_bits = gaitem_handle & 0xF0000000
        cursor = offset + cls.BASE_SIZE
        size = cls.BASE_SIZE

        durability = unk_1 = unk_2 = 0
        effect_1 = effect_2 = effect_3 = 0
        sec_effect1 = sec_effect2 = sec_effect3 = 0
        padding = ()

        if gaitem_handle != 0:
            if type_bits == ITEM_TYPE_WEAPON:
                cursor += 80
                size = cursor - offset
            elif type_bits == ITEM_TYPE_ARMOR:
                cursor += 8
                size = cursor - offset
            elif type_bits == ITEM_TYPE_RELIC:
                # Check bounds before each read to handle corrupted/truncated saves
                if cursor + 8 > data_len:
                    return cls(gaitem_handle, item_id, 0, 0, 0, 0, 0, 0, 0, 0, 0, offset, size=cls.BASE_SIZE)
                durability, unk_1 = struct.unpack_from("<II", data_type, cursor)
                cursor += 8

                if cursor + 12 > data_len:
                    return cls(gaitem_handle, item_id, 0, 0, 0, durability, unk_1, 0, 0, 0, 0, offset, size=cursor-offset)
                effect_1, effect_2, effect_3 = struct.unpack_from("<III", data_type, cursor)
                cursor += 12

                if cursor + 0x1C > data_len:
                    return cls(gaitem_handle, item_id, effect_1, effect_2, effect_3, durability, unk_1, 0, 0, 0, 0, offset, size=cursor-offset)
                padding = struct.unpack_from("<7I", data_type, cursor)
                cursor += 0x1C

                if cursor + 12 > data_len:
                    return cls(gaitem_handle, item_id, effect_1, effect_2, effect_3, durability, unk_1, 0, 0, 0, 0, offset, extra=padding, size=cursor-offset)
                sec_effect1, sec_effect2, sec_effect3 = struct.unpack_from("<III", data_type, cursor)
                cursor += 12

                if cursor + 4 > data_len:
                    return cls(gaitem_handle, item_id, effect_1, effect_2, effect_3, durability, unk_1, sec_effect1, sec_effect2, sec_effect3, 0, offset, extra=padding, size=cursor-offset)
                unk_2 = struct.unpack_from("<I", data_type, cursor)[0]
                cursor += 12
                size = cursor - offset

        return cls(gaitem_handle, item_id, effect_1, effect_2, effect_3,
                   durability, unk_1, sec_effect1, sec_effect2, sec_effect3,
                   unk_2, offset, extra=padding, size=size)


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
            return "Unlnown"
        else:
            try:
                row = self._name_df[self._name_df["id"] == self.text_id]
                if not row.empty:
                    return row["text"].values[0]
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
