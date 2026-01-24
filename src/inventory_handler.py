import struct
from basic_class import ItemEntry, ItemState
import globals
import logging


logger = logging.getLogger(__name__)


class InventoryHandler:
    START_OFFEST = 0x14
    STATE_SLOT_COUNT = 5120
    ENTRY_SLOT_COUNT = 3065
    STATE_SLOT_KEEP_COUNT = 84

    def __init__(self):
        self.states: list[ItemState] = []
        self.entries: list[ItemEntry] = []
        self.player_name_offset = 0
        self.entry_offset = 0
        self.entry_count = 0
        self.vessels = [9600, 9603, 9606, 9609, 9612, 9615, 9618, 9621, 9900, 9910]  # Hero Default
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

    def parse(self):
        logger.info("Parsing inventory data")
        self.__init__()
        cur_offset = self.START_OFFEST
        logger.info("Parsing inventory states. Starting at offset: 0x%X", cur_offset)
        for i in range(self.STATE_SLOT_COUNT):
            state = ItemState()
            state.from_bytes(globals.data, cur_offset)
            self.states.append(state)
            self._cur_last_instance_id = max(self._cur_last_instance_id, state.instance_id)
            self._cur_last_state_index = i if state.ga_handle != 0 else self._cur_last_state_index
            cur_offset += state.size

        cur_offset += 0x94
        self.player_name_offset = cur_offset
        logger.info("Assuming player name offset at: 0x%X", cur_offset)
        cur_offset += 0x5B8
        self.entry_offset = cur_offset
        logger.info("Assuming entry offset at: 0x%X", cur_offset)
        cur_offset += 0x4

        logger.info("Parsing inventory entries. Starting at offset: 0x%X", cur_offset)
        for i in range(self.ENTRY_SLOT_COUNT):
            entry = ItemEntry(globals.data[cur_offset:cur_offset+14])
            self.entries.append(entry)
            if entry.item_id in range(9600, 9957):
                self.vessels.append(entry.item_id)
            cur_offset += 14
            if entry.ga_handle != 0:
                self.entry_count += 1
            self._cur_last_acquisition_id = max(self._cur_last_acquisition_id, entry.acquisition_id)

        count_in_data = struct.unpack_from("<I", globals.data, self.entry_offset)[0]
        if self.entry_count != count_in_data:
            logger.warning("Entry count mismatch: counted %d, data has %d", self.entry_count, count_in_data)
            logger.warning("Trying to fix it...")
            logger.info("Updating entry count in")
            struct.pack_into("<I", globals.data, self.entry_offset, self.entry_count)

    def debug_print(self):
        for i, state in enumerate(self.states):
            logger.debug(f"State {i}: {state}")
        for i, entry in enumerate(self.entries):
            logger.debug(f"Entry {i}: {entry}")
        logger.debug(f"Player Name Offset: {self.player_name_offset}")
        logger.debug(f"Entry Offset: {self.entry_offset}")
        logger.debug(f"Entry Count: {self.entry_count}")
        logger.debug(f"Vessels: {self.vessels}")
        logger.debug(f"Last Instance ID: {self._cur_last_instance_id}")
        logger.debug(f"Last Acquisition ID: {self._cur_last_acquisition_id}")
        logger.debug(f"Last State Index: {self._cur_last_state_index}")
