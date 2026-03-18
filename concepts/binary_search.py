from manim import *

class BinarySearchVisualization(Scene):
    def construct(self):

        array = [2,5,8,12,16,23,38,56,72]
        target = 23

        squares = VGroup()
        labels = VGroup()

        for i,n in enumerate(array):
            s = Square(side_length=0.8)
            s.move_to(RIGHT*i)
            t = Text(str(n), font_size=30).move_to(s)
            squares.add(s)
            labels.add(t)

        group = VGroup(squares, labels).move_to(ORIGIN)

        self.play(Create(squares), Write(labels))
        self.wait()

        left = 0
        right = len(array)-1

        left_arrow = Arrow(UP, DOWN).next_to(squares[left], UP)
        right_arrow = Arrow(UP, DOWN).next_to(squares[right], UP)

        self.play(Create(left_arrow), Create(right_arrow))

        while left <= right:

            mid = (left+right)//2

            mid_arrow = Arrow(DOWN, UP, color=YELLOW).next_to(squares[mid], DOWN)
            self.play(Create(mid_arrow))

            self.play(squares[mid].animate.set_fill(YELLOW, opacity=0.5))
            self.wait()

            if array[mid] == target:

                found = Text("Found!", color=GREEN).to_edge(UP)
                self.play(Write(found))
                self.wait(2)
                return

            if array[mid] < target:
                left = mid+1
                self.play(left_arrow.animate.next_to(squares[left], UP))
            else:
                right = mid-1
                self.play(right_arrow.animate.next_to(squares[right], UP))

            self.play(FadeOut(mid_arrow))