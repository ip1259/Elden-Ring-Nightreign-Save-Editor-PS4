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


class ItemState:
    BASE_SIZE = 8

    def __init__(self):
        self.ga_handle = 0
        self.instance_id = 0
        self.item_id = 0xffffffff
        self.real_item_id = 0x00ffffff
        self.type_bits = 0
        self.data: bytearray = bytes.fromhex('00000000FFFFFFFF')
        self.size = 8

    @classmethod
    def create_dummy_relic(cls, instance_id, relic_type: str = "normal"):
        if relic_type.lower() == "normal":
            real_item_id = 100
            item_id = 0x80000000 | (real_item_id & 0x00FFFFFF)
            dummy_effect_id = 7000000
        elif relic_type.lower() == "deep":
            real_item_id = 2003000
            item_id = 0x80000000 | (real_item_id & 0x00FFFFFF)
            dummy_effect_id = 7001002
        else:
            raise ValueError("Invalid relic type")
        dummy_relic = cls()
        dummy_relic.ga_handle = 0xC0000000 | (instance_id & 0x00FFFFFF)
        dummy_relic.item_id = item_id
        dummy_relic.instance_id = instance_id
        dummy_relic.real_item_id = real_item_id
        dummy_relic.type_bits = ITEM_TYPE_RELIC
        dummy_relic.size = 80
        _padding = bytes([
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0xFF,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF,
            0xFF, 0xFF, 0xFF, 0xFF
        ])

        _data: bytearray = bytearray(80)
        struct.pack_into("<I", _data, 0, dummy_relic.ga_handle)  # ga_handle
        struct.pack_into("<I", _data, 4, dummy_relic.item_id)  # item_id : real_id->100 Delicate Burning Scene/id->2003000 Deep Delicate Burning Scene
        struct.pack_into("<I", _data, 8, dummy_relic.item_id)  # durability (same as item_id when item is a relic)
        struct.pack_into("<I", _data, 12, int(0xffffffff))  # unk_1
        struct.pack_into("<I", _data, 16, int(dummy_effect_id))  # effect_1:Normal-> Vigor + 1(id: 7000000) / Deep -> Poise +3(id:7001002)
        struct.pack_into("<I", _data, 20, int(0xffffffff))  # effect_2
        struct.pack_into("<I", _data, 24, int(0xffffffff))  # effect_3
        _data = _data[:28] + _padding + _data[28+len(_padding):]  # add padding
        struct.pack_into("<I", _data, 56, int(0xffffffff))  # curse_1
        struct.pack_into("<I", _data, 60, int(0xffffffff))  # curse_2
        struct.pack_into("<I", _data, 64, int(0xffffffff))  # curse_3
        struct.pack_into("<I", _data, 68, int(0xffffffff))  # unk_2
        struct.pack_into("<Q", _data, 72, int(0))  # 8 bytes end_padding

        dummy_relic.data = _data
        return dummy_relic

    def from_bytes(self, user_data: bytearray, offset=0):
        data_len = len(user_data)

        # Check if we have enough data for the base read
        if offset + self.BASE_SIZE > data_len:
            raise ValueError("Invalid data length. Save File may be corrupted.")

        self.ga_handle, self.item_id = struct.unpack_from("<II", user_data, offset)
        self.type_bits = self.ga_handle & 0xF0000000
        self.instance_id = self.ga_handle & 0x00FFFFFF
        self.real_item_id = self.item_id & 0x00FFFFFF
        cursor = offset

        if self.ga_handle != 0:
            if self.type_bits == ITEM_TYPE_WEAPON:
                if cursor + 88 > data_len:
                    raise ValueError("Invalid data length. Save File may be corrupted.")
                self.size = 88
                self.data = user_data[cursor:cursor+self.size]
            elif self.type_bits == ITEM_TYPE_ARMOR:
                if cursor + 16 > data_len:
                    raise ValueError("Invalid data length. Save File may be corrupted.")
                self.size = 16
                self.data = user_data[cursor:cursor+self.size]
            elif self.type_bits == ITEM_TYPE_RELIC:
                if cursor + 80 > data_len:
                    raise ValueError("Invalid data length. Save File may be corrupted.")
                self.size = 80
                self.data = user_data[cursor:cursor+self.size]

    def set_real_id(self, real_id):
        if self.type_bits != ITEM_TYPE_RELIC:
            raise TypeError("Real ID can only be set for relics")
        self.real_item_id = real_id
        self.item_id = self.real_item_id | 0x80000000
        struct.pack_into("<I", self.data, 4, self.item_id)
        self.durability = self.item_id

    @property
    def durability(self):
        if self.type_bits != ITEM_TYPE_RELIC:
            return None
        return struct.unpack_from("<I", self.data, 8)[0]

    @durability.setter
    def durability(self, value):
        if self.type_bits != ITEM_TYPE_RELIC:
            raise TypeError("Durability can only be set for relics")
        struct.pack_into("<I", self.data, 8, value)

    @property
    def unk_1(self):
        if self.type_bits != ITEM_TYPE_RELIC:
            return None
        return struct.unpack_from("<I", self.data, 12)[0]

    @unk_1.setter
    def unk_1(self, value):
        if self.type_bits != ITEM_TYPE_RELIC:
            raise TypeError("Unk_1 can only be set for relics")
        struct.pack_into("<I", self.data, 12, value)

    @property
    def effect_1(self):
        if self.type_bits != ITEM_TYPE_RELIC:
            return None
        return struct.unpack_from("<I", self.data, 16)[0]

    @effect_1.setter
    def effect_1(self, value):
        if self.type_bits != ITEM_TYPE_RELIC:
            raise TypeError("Effect_1 can only be set for relics")
        struct.pack_into("<I", self.data, 16, value)

    @property
    def effect_2(self):
        if self.type_bits != ITEM_TYPE_RELIC:
            return None
        return struct.unpack_from("<I", self.data, 20)[0]

    @effect_2.setter
    def effect_2(self, value):
        if self.type_bits != ITEM_TYPE_RELIC:
            raise TypeError("Effect_2 can only be set for relics")
        struct.pack_into("<I", self.data, 20, value)

    @property
    def effect_3(self):
        if self.type_bits != ITEM_TYPE_RELIC:
            return None
        return struct.unpack_from("<I", self.data, 24)[0]

    @effect_3.setter
    def effect_3(self, value):
        if self.type_bits != ITEM_TYPE_RELIC:
            raise TypeError("Effect_3 can only be set for relics")
        struct.pack_into("<I", self.data, 24, value)

    @property
    def curse_1(self):
        if self.type_bits != ITEM_TYPE_RELIC:
            return None
        return struct.unpack_from("<I", self.data, 56)[0]

    @curse_1.setter
    def curse_1(self, value):
        if self.type_bits != ITEM_TYPE_RELIC:
            raise TypeError("Curse_1 can only be set for relics")
        struct.pack_into("<I", self.data, 56, value)

    @property
    def curse_2(self):
        if self.type_bits != ITEM_TYPE_RELIC:
            return None
        return struct.unpack_from("<I", self.data, 60)[0]

    @curse_2.setter
    def curse_2(self, value):
        if self.type_bits != ITEM_TYPE_RELIC:
            raise TypeError("Curse_2 can only be set for relics")
        struct.pack_into("<I", self.data, 60, value)

    @property
    def curse_3(self):
        if self.type_bits != ITEM_TYPE_RELIC:
            return None
        return struct.unpack_from("<I", self.data, 64)[0]

    @curse_3.setter
    def curse_3(self, value):
        if self.type_bits != ITEM_TYPE_RELIC:
            raise TypeError("Curse_3 can only be set for relics")
        struct.pack_into("<I", self.data, 64, value)

    @property
    def unk_2(self):
        if self.type_bits != ITEM_TYPE_RELIC:
            return None
        return struct.unpack_from("<I", self.data, 68)[0]

    @unk_2.setter
    def unk_2(self, value):
        if self.type_bits != ITEM_TYPE_RELIC:
            raise TypeError("Unk_2 can only be set for relics")
        struct.pack_into("<I", self.data, 68, value)

    @property
    def effects_and_curses(self):
        if self.type_bits != ITEM_TYPE_RELIC:
            return None
        return [self.effect_1, self.effect_2, self.effect_3, self.curse_1, self.curse_2, self.curse_3]

    def __repr__(self):
        return f"ItemState(ga_handle=0x{self.ga_handle:08X}, item_id=0x{self.item_id:08X}, instance_id={self.instance_id}, real_item_id={self.real_item_id}, type_bits=0x{self.type_bits:08X}, size={self.size})"


class ItemEntry:
    # First 4 bytes: Item count
    # Followed by ItemEntry structures (Base size 14 bytes):
    # - 4 bytes: ga_handle, Composite LE (Byte 0: Type 0xB0=Goods, 0xC0=Relics etc. Bytes 1-3: ID)
    # - 4 bytes: item_quantity, 0xB00003E9 -> GoodsId = 1001, Flask of Crimson Tears Default Quantity is 3
    # - 4 bytes: acquisition ID, Unique, this value does not repeat across all item entries.
    # - 1 byte: bool -> is favorite
    # - 1 byte: bool -> is salable, if favorite, unique relic, equipped will be false
    def __init__(self, data_bytes: bytearray):
        if len(data_bytes) != 14:
            raise ValueError("Invalid data length")
        self.ga_handle = struct.unpack_from("<I", data_bytes, 0)[0]
        self.type_bits = self.ga_handle & 0xF0000000
        self.item_id = self.ga_handle & 0x00FFFFFF
        self.item_amount = struct.unpack_from("<I", data_bytes, 4)[0]
        self.acquisition_id = struct.unpack_from("<I", data_bytes, 8)[0]
        self.is_favorite = bool(data_bytes[12])
        self.is_salable = bool(data_bytes[13])
        self.state: ItemState = None

    @classmethod
    def create_from_state(cls, state: ItemState, acquisition_id: int):
        entry = cls(bytearray(14))
        entry.ga_handle = state.ga_handle
        entry.item_id = state.item_id
        entry.item_amount = 1
        entry.acquisition_id = acquisition_id
        entry.is_favorite = True
        entry.is_salable = False
        return entry

    @property
    def data_bytes(self):
        _data = bytearray(14)
        struct.pack_into("<I", _data, 0, self.ga_handle)
        struct.pack_into("<I", _data, 4, self.item_amount)
        struct.pack_into("<I", _data, 8, self.acquisition_id)
        _data[12] = int(self.is_favorite)
        _data[13] = int(self.is_salable)
        return _data

    @property
    def is_relic(self):
        return self.type_bits == ITEM_TYPE_RELIC

    def link_state(self, state: ItemState):
        self.state = state

    def __repr__(self):
        return f"ItemEntry(ga_handle=0x{self.ga_handle:08X}, item_id={self.item_id}, item_amount={self.item_amount}, acquisition_id={self.acquisition_id}, is_favorite={self.is_favorite}, is_sellable={self.is_salable})"


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

    def is_deep(self):
        if self._is_empty_id or self._is_unknown:
            return False
        return self._relic_df["isDeepRelic"].values[0] == 1

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
