class InstanceWrapper:

    def __init__(self, instance, pos):
        self.x = pos[0]
        self.y = pos[1]
        self.instance = instance
        self.vector = Vector(self.x, self.y)
        # Offset from the rocket's center of mass, in the unrotated (rotation=0) build layout.
        self.local_dx = 0.0
        self.local_dy = 0.0

    def get_pos(self):
        return (self.x, self.y)