def draw_rocket(rocket, assets, surface):
    for instance in rocket.parts:
        image = assets.get_image(instance.part_def.sprite)
        rect = image.get_rect(midbottom=instance.screen_position)
        surface.blit(image, rect)