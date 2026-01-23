import struct
from globals import ITEM_TYPE_WEAPON, ITEM_TYPE_ARMOR, ITEM_TYPE_RELIC
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
