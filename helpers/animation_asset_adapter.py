class AnimationAssetAdapter:
    def __init__(self, sprite_dir="Sprites/parts/", default_size=(64, 64)):
        self.sprite_dir = sprite_dir
        self.default_size = default_size
        self._cache = {}

    def get_image(self, filename: str):
        if filename not in self._cache:
            path = f"{self.sprite_dir}{filename}"
            image = pygame.image.load(path).convert_alpha()
            if image.get_size() != self.default_size:
                image = pygame.transform.smoothscale(image, self.default_size)
            self._cache[filename] = image
        return self._cache[filename]