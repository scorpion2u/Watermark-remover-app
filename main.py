from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

class Root(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.add_widget(Label(text='Watermark Remover (demo)'))
        btn = Button(text='点击测试')
        btn.bind(on_press=lambda *_: print('Button pressed'))
        self.add_widget(btn)

class DemoApp(App):
    def build(self):
        return Root()

if __name__ == '__main__':
    DemoApp().run()
