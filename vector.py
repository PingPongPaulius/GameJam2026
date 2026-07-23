import math

class Vector:

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):
        return Vector(self.x + other.x, self.y+other.y)
    
    def __sub__(self, other):
        return Vector(self.x - other.x, self.y - other.y)

    def __mul__(self, other):
        return Vector2D(self.x * other, self.y * other)
    
    def dot(self, otehr):
        return self.x * other.x + self.y * other.y

    def mag(self):
        return math.sqrt(self.x**2 + self.y**2)

    def length(self, other):
        return Vector(self.x - other.x, self.y - other.y)

    def normalized(self):
        return self * (1/self.magnitude())
