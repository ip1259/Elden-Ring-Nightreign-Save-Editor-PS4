import struct
from basic_class import ItemEntry, ItemState
import globals
import logging
import threading


logger = logging.getLogger(__name__)


def remove_padding_area():
    # Remove 72 bytes from the padding area at the end of the file.
    # The save file must maintain a constant size for the game to load it.
    globals.data = globals.data[: -0x1C - 72] + globals.data[-0x1C:]


def insert_padding_area():
    # Insert 72 bytes of padding at the end of the file.
    # The save file must maintain a constant size for the game to load it.
    globals.data = globals.data[: -0x1C] + b'\x00' * 72 + globals.data[-0x1C:]


class InventoryHandler:
    _instance = None
    _lock = threading.Lock()
    _parse_lock = threading.Lock()
    _initialized = False

    START_OFFEST = 0x14
    STATE_SLOT_COUNT = 5120
    ENTRY_SLOT_COUNT = 3065
    STATE_SLOT_KEEP_COUNT = 84

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(InventoryHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        with self._lock:
            self.initialize()

    def initialize(self):
        self._initialized = True
        self.states: list[ItemState] = []
        self.entries: list[ItemEntry] = []
        self.relics: dict[int, ItemEntry] = {}
        self.player_name_offset = 0
        self.entry_count_offset = 0
        self.entry_offset = 0
        self.entry_count = 0
        self.vessels = [9600, 9603, 9606, 9609, 9612, 9615, 9618, 9621, 9900, 9910]  # Hero Default
        self.ga_to_acquisition_id = {}
        self._cur_last_instance_id = 0x800054  # start instance id
        self._cur_last_acquisition_id = 0
        self._cur_last_state_index = 0

    @classmethod
    def get_player_name_from_data(cls, data):
        cur_offset = cls.START_OFFEST
        for i in range(cls.STATE_SLOT_COUNT):
            state = ItemState()
            state.from_bytes(data, cur_offset)
            cur_offset += state.size
        cur_offset += 0x94
        max_chars = 16
        for cur in range(cur_offset, cur_offset + max_chars * 2, 2):
            if data[cur:cur + 2] == b'\x00\x00':
                max_chars = (cur - cur_offset) // 2
                break
        raw_name = data[cur_offset:cur_offset + max_chars * 2]
        name = raw_name.decode("utf-16-le", errors="ignore").rstrip("\x00")
        return name if name else None

    def aquire_new_instance_id(self):
        self._cur_last_instance_id += 1
        return self._cur_last_instance_id

    def aquire_new_acquisition_id(self):
        self._cur_last_acquisition_id += 1
        return self._cur_last_acquisition_id

    def parse(self):
        if self._parse_lock.acquire(blocking=False):
            try:
                logger.info("Parsing inventory data")
                self.initialize()
                cur_offset = self.START_OFFEST
                state_ga_to_index = {}
                logger.info("Parsing inventory states. Starting at offset: 0x%X", cur_offset)
                for i in range(self.STATE_SLOT_COUNT):
                    state = ItemState()
                    state.from_bytes(globals.data, cur_offset)
                    self.states.append(state)
                    if state.ga_handle != 0:
                        state_ga_to_index[state.ga_handle] = i
                    self._cur_last_instance_id = max(self._cur_last_instance_id, state.instance_id)
                    self._cur_last_state_index = i if state.ga_handle != 0 else self._cur_last_state_index
                    cur_offset += state.size

                cur_offset += 0x94
                self.player_name_offset = cur_offset
                logger.info("Assuming player name offset at: 0x%X", cur_offset)
                cur_offset += 0x5B8
                self.entry_count_offset = cur_offset
                logger.info("Assuming entry count offset at: 0x%X", cur_offset)
                cur_offset += 0x4
                self.entry_offset = cur_offset
                logger.info("Assuming entry offset at: 0x%X", cur_offset)

                logger.info("Parsing inventory entries. Starting at offset: 0x%X", cur_offset)
                for i in range(self.ENTRY_SLOT_COUNT):
                    entry = ItemEntry(globals.data[cur_offset:cur_offset+14])
                    self.entries.append(entry)
                    if entry.item_id in range(9600, 9957):
                        self.vessels.append(entry.item_id)
                    cur_offset += 14
                    if entry.ga_handle != 0:
                        self.ga_to_acquisition_id[entry.ga_handle] = entry.acquisition_id
                        self.entry_count += 1
                    self._cur_last_acquisition_id = max(self._cur_last_acquisition_id, entry.acquisition_id)
                    if entry.is_relic:
                        entry.link_state(self.states[state_ga_to_index[entry.ga_handle]])
                        self.relics[entry.item_id] = entry

                count_in_data = struct.unpack_from("<I", globals.data, self.entry_count_offset)[0]
                if self.entry_count != count_in_data:
                    logger.warning("Entry count mismatch: counted %d, data has %d", self.entry_count, count_in_data)
                    logger.warning("Trying to fix it...")
                    logger.info("Updating entry count in")
                    struct.pack_into("<I", globals.data, self.entry_count_offset, self.entry_count)
            finally:
                self._parse_lock.release()

    def add_relic_to_inventory(self):
        logger.info("Adding relic to inventory")
        # Create dummy relic state first
        dummy_relic = ItemState.create_dummy_relic(self.aquire_new_instance_id())
        # Replace Item Entry at empty slot
        empty_entry_index = -1
        for i in range(self.ENTRY_SLOT_COUNT):
            entry = self.entries[i]
            if entry.ga_handle == 0:
                # Found an empty slot
                empty_entry_index = i
                break
        else:
            raise RuntimeError("No empty slot found in inventory entries to add relic.")

        # Replace Item State after current last item state
        empty_state_index = -1
        for i in range(self._cur_last_state_index, self.STATE_SLOT_COUNT):
            if self.states[i].ga_handle == 0:
                empty_state_index = i
                break
        else:
            raise RuntimeError("No empty slot found in inventory states to add relic.")

        # Replace Item Entry
        self.entries[empty_entry_index] = ItemEntry.create_from_state(dummy_relic, self.aquire_new_acquisition_id())
        _new_enty_data = self.entries[empty_entry_index].data_bytes
        # Replace entry data
        target_offset = self.entry_offset + empty_entry_index * 14
        logger.info("Adding relic at offset: 0x%X", target_offset)
        globals.data = globals.data[:self.entry_offset+empty_entry_index*14] + _new_enty_data + globals.data[self.entry_offset+(empty_entry_index+1)*14:]
        # Update entry count
        self.entry_count += 1
        struct.pack_into("<I", globals.data, self.entry_count_offset, self.entry_count)
        logger.info("Added relic at entry index %d", empty_entry_index)

        # Replace Item State data
        old_size = self.states[empty_state_index].size
        self.states[empty_state_index] = dummy_relic
        _new_state_data = self.states[empty_state_index].data
        _cur_offset = self.START_OFFEST + sum(state.size for state in self.states[:empty_state_index])
        globals.data = globals.data[:_cur_offset] + _new_state_data + globals.data[_cur_offset + old_size:]
        remove_padding_area()
        logger.info("Added relic at state index %d", empty_state_index)
        self._cur_last_state_index = empty_state_index
        self.parse()  # Just make sure everything is fine
        return True, self.entries[empty_entry_index].ga_handle

    def remove_relic_from_inventory(self, ga_handel):
        logger.info("Removing relic from inventory")
        target_state_index = -1
        for i in range(self.STATE_SLOT_COUNT):
            if self.states[i].ga_handle == ga_handel:
                target_state_index = i
                logger.info("Found relic at state index %d", target_state_index)
                break
        else:
            raise ValueError("Relic not found in inventory")
        target_entry_index = -1
        for i in range(self.ENTRY_SLOT_COUNT):
            if self.entries[i].ga_handle == ga_handel:
                target_entry_index = i
                logger.info("Found relic at entry index %d", target_entry_index)
                break
        else:
            raise ValueError("Relic not found in inventory")

        # Replace target entry by 0
        logger.info("Removing relic at entry index %d", target_entry_index)
        self.entries[target_entry_index] = ItemEntry(bytearray(14))
        _new_enty_data = self.entries[target_entry_index].data_bytes
        globals.data = globals.data[:self.entry_offset+target_entry_index*14] + _new_enty_data + globals.data[self.entry_offset+(target_entry_index+1)*14:]
        # Update entry count
        logger.info(f"Updating entry count in inventory from {self.entry_count} to {self.entry_count - 1}")
        self.entry_count -= 1
        struct.pack_into("<I", globals.data, self.entry_count_offset, self.entry_count)
        logger.info("Removed relic at entry index %d", target_entry_index)

        # Replace target state by 0
        logger.info("Removing relic at state index %d", target_state_index)
        old_size = self.states[target_state_index].size
        self.states[target_state_index] = ItemState()
        _new_state_data = self.states[target_state_index].data
        _cur_offset = self.START_OFFEST + sum(state.size for state in self.states[:target_state_index])
        globals.data = globals.data[:_cur_offset] + _new_state_data + globals.data[_cur_offset + old_size:]
        logger.info("Fill padding area with 0x00")
        insert_padding_area()
        logger.info("Removed relic at state index %d", target_state_index)
        self._cur_last_state_index = target_state_index-1
        self.parse()  # Just make sure everything is fine
        return True

    def update_relic_state(self, state_index):
        logger.info("Updating relic state")
        # Only relics can have their state updated
        if self.states[state_index].type_bits != globals.ITEM_TYPE_RELIC:
            raise TypeError("Only relics can have their state updated")

        # Assume item type wasn't change
        target_offset = self.START_OFFEST + sum(state.size for state in self.states[:state_index])
        globals.data = globals.data[:target_offset] + self.states[state_index].data + globals.data[target_offset + self.states[state_index].size:]
        self.parse()  # Just make sure everything is fine

    def modify_relic(self, ga_handle, relic_id=None,
                     effect_1=None, effect_2=None, effect_3=None,
                     curse_1=None, curse_2=None, curse_3=None):
        type_bits = ga_handle & 0xF0000000
        if type_bits != globals.ITEM_TYPE_RELIC:
            raise TypeError("Only relics can be modified")

        logger.info("Modifying relic in inventory")
        target_state_index = -1
        for i in range(self.STATE_SLOT_KEEP_COUNT, self.STATE_SLOT_COUNT):
            if self.states[i].ga_handle == ga_handle:
                target_state_index = i
                if relic_id is not None:
                    self.states[target_state_index].set_real_id(relic_id)
                if effect_1 is not None:
                    self.states[target_state_index].effect_1 = effect_1
                if effect_2 is not None:
                    self.states[target_state_index].effect_2 = effect_2
                if effect_3 is not None:
                    self.states[target_state_index].effect_3 = effect_3
                if curse_1 is not None:
                    self.states[target_state_index].curse_1 = curse_1
                if curse_2 is not None:
                    self.states[target_state_index].curse_2 = curse_2
                if curse_3 is not None:
                    self.states[target_state_index].curse_3 = curse_3
                break
        else:
            raise ValueError("Relic not found in inventory")
        self.update_relic_state(target_state_index)
        return True

    def debug_print(self, non_zero_only=False):
        for i, state in enumerate(self.states):
            if state.ga_handle == 0 and non_zero_only:
                continue
            logger.debug(f"State {i}: {state}")
        for i, entry in enumerate(self.entries):
            if entry.ga_handle == 0 and non_zero_only:
                continue
            logger.debug(f"Entry {i}: {entry}")
        logger.debug(f"Player Name Offset: {self.player_name_offset}")
        logger.debug(f"Entry Offset: {self.entry_count_offset}")
        logger.debug(f"Entry Count: {self.entry_count}")
        logger.debug(f"Vessels: {self.vessels}")
        logger.debug(f"Last Instance ID: {self._cur_last_instance_id}")
        logger.debug(f"Last Acquisition ID: {self._cur_last_acquisition_id}")
        logger.debug(f"Last State Index: {self._cur_last_state_index}")
