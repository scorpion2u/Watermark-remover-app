from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.graphics.texture import Texture
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import io, os

class Editor(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.filechooser = FileChooserIconView(size_hint_y=0.4)
        self.filechooser.filters = ['*.png', '*.jpg', '*.jpeg', '*.bmp']
        self.filechooser.bind(on_submit=self.load_image_from_filechooser)
        self.add_widget(self.filechooser)

        self.image_display = KivyImage(size_hint_y=0.5)
        self.add_widget(self.image_display)

        controls = BoxLayout(size_hint_y=0.1)
        btn_load = Button(text='Load Selected', on_press=self.load_image_selected)
        btn_save = Button(text='Save Image', on_press=self.save_image)
        controls.add_widget(btn_load)
        controls.add_widget(btn_save)
        self.add_widget(controls)

        adjust_row = BoxLayout(size_hint_y=0.1)
        adjust_row.add_widget(Label(text='Brightness'))
        self.bright = Slider(min=0.2, max=2.0, value=1.0)
        adjust_row.add_widget(self.bright)
        apply_btn = Button(text='Apply Brightness', size_hint_x=0.4, on_press=self.apply_brightness)
        adjust_row.add_widget(apply_btn)
        self.add_widget(adjust_row)

        watermark_row = BoxLayout(size_hint_y=0.1)
        self.wm_text = Label(text='Watermark: (adds watermark to image for ownership)')
        wm_btn = Button(text='Add Watermark', on_press=self.add_watermark)
        watermark_row.add_widget(self.wm_text)
        watermark_row.add_widget(wm_btn)
        self.add_widget(watermark_row)

        self.current_image = None
        self.current_path = None

    def load_image_from_filechooser(self, chooser, selection, touch):
        if selection:
            self.load_image(selection[0])

    def load_image_selected(self, instance):
        sel = self.filechooser.selection
        if sel:
            self.load_image(sel[0])

    def load_image(self, path):
        try:
            img = Image.open(path).convert('RGBA')
            self.current_image = img.copy()
            self.current_path = path
            self.update_display(img)
        except Exception as e:
            print('Failed to load image:', e)

    def pil_to_texture(self, pil_image):
        pil_image = pil_image.convert('RGBA')
        w, h = pil_image.size
        data = pil_image.tobytes()
        texture = Texture.create(size=(w, h))
        texture.blit_buffer(data, colorfmt='rgba', bufferfmt='ubyte')
        texture.flip_vertical()
        return texture

    def update_display(self, pil_img):
        tex = self.pil_to_texture(pil_img)
        self.image_display.texture = tex

    def apply_brightness(self, instance):
        if self.current_image:
            enhancer = ImageEnhance.Brightness(self.current_image)
            out = enhancer.enhance(self.bright.value)
            self.current_image = out
            self.update_display(out)

    def add_watermark(self, instance):
        if not self.current_image:
            return
        img = self.current_image.convert('RGBA')
        txt = Image.new('RGBA', img.size, (255,255,255,0))
        draw = ImageDraw.Draw(txt)
        try:
            font = ImageFont.load_default()
        except:
            font = None
        text = "© YourName"
        w, h = img.size
        draw.text((w-10-100, h-10-20), text, fill=(255,255,255,180), font=font)
        out = Image.alpha_composite(img, txt)
        self.current_image = out.convert('RGB')
        self.update_display(self.current_image)

    def save_image(self, instance):
        if not self.current_image:
            return
        save_path = os.path.join(os.path.expanduser('~'), 'watermark_editor_saved.jpg')
        try:
            self.current_image.convert('RGB').save(save_path, 'JPEG', quality=90)
            print('Saved to', save_path)
        except Exception as e:
            print('Failed to save image:', e)


class EditorApp(App):
    def build(self):
        return Editor()

if __name__ == '__main__':
    EditorApp().run()
