import pygame

from UI import Label, Button
import random as rng


class THE_END:

    def __init__(self, score: int):
        
        self.end_screen = [f"GG Your Score {score} score", f"At Least you tried: {score} score", f"What a machine you are with the height {score}"]
        self.label = Label(rng.choise(end_screen))
        self.reset_button = Button(0,0,100,40,label="TRY AGAIN")

    def render(self, g):
        
        self.label.render(g, (100, 100))
        self.reset_button.render(g)

    def update(self) -> bool:

        return self.reset_button.update() == "Pressed"
