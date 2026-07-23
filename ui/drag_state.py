class DragState:
    def __init__(self):
        self.active = False
        self.part_def = None
        self.mouse_pos = (0, 0)
        self.target_slot = None
        self.target_offset_x = 0.0

    def start(self, part_def, mouse_pos):
        self.active = True
        self.part_def = part_def
        self.mouse_pos = mouse_pos
        self.target_slot = None

    def update(self, mouse_pos, target_slot, target_offset_x):
        self.mouse_pos = mouse_pos
        self.target_slot = target_slot
        self.target_offset_x = target_offset_x

    def cancel(self):
        self.active = False
        self.part_def = None
        self.target_slot = None