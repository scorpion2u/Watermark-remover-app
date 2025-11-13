# main.py
# Kivy GUI app for offline watermark removal (automatic + manual mask + save)
# Note: Requires Kivy, OpenCV (cv2), Pillow, numpy.
# UI: Open image -> 自动检测掩膜 -> 按钮 Inpaint -> 保存结果
# Also allows 手动绘制掩膜（轻量）

from kivy.config import Config
Config.set('graphics', 'resizable', True)

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics.texture import Texture
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.clock import mainthread

import cv2
import numpy as np
from PIL import Image
import io
import os
from functools import partial
from threading import Thread

KV = '''
<RootWidget>:
    orientation: 'vertical'
    padding: 8
    spacing: 8

    BoxLayout:
        size_hint_y: None
        height: '44dp'
        spacing: 8
        Button:
            text: '打开图片'
            on_release: root.open_image()
        Button:
            text: '自动检测并去水印'
            on_release: root.auto_process()
        Button:
            text: '手动绘制掩膜'
            on_release: root.toggle_paint_mode()
        Button:
            text: '保存结果'
            on_release: root.save_result()

    Image:
        id: img_display
        allow_stretch: True
        keep_ratio: True

    Label:
        id: status
        size_hint_y: None
        height: '24dp'
        text: '状态：就绪'
'''

class RootWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.image_path = None
        self.cv_img = None        # original BGR
        self.result_img = None    # processed BGR
        self.mask = None          # mask uint8 0/255 (same size as image)
        self.paint_mode = False
        self.brush_size = 25

        # painting overlay
        self._painting = False
        self._last = None

        # touch bind for manual paint
        self.ids = None

    def open_image(self):
        # Use filechooser popup - Kivy's FileChooser may vary by platform; use builtin
        from kivy.uix.filechooser import FileChooserListView
        content = BoxLayout(orientation='vertical')
        fc = FileChooserListView(filters=['*.png', '*.jpg', '*.jpeg', '*.bmp'])
        content.add_widget(fc)
        btns = BoxLayout(size_hint_y=None, height='40dp')
        from kivy.uix.button import Button
        ok = Button(text='打开')
        cancel = Button(text='取消')
        btns.add_widget(ok)
        btns.add_widget(cancel)
        content.add_widget(btns)
        popup = Popup(title='选择图片', content=content, size_hint=(0.9, 0.9))
        ok.bind(on_release=lambda *a: self._load_from_path(fc.path, fc.selection, popup))
        cancel.bind(on_release=lambda *a: popup.dismiss())
        popup.open()

    def _load_from_path(self, path, selection, popup):
        popup.dismiss()
        if not selection:
            self.set_status('未选择文件')
            return
        p = selection[0]
        try:
            img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                self.set_status('无法读取图片')
                return
            self.image_path = p
            self.cv_img = img
            self.result_img = img.copy()
            self.mask = np.zeros(img.shape[:2], dtype=np.uint8)
            self.update_display(self.cv_img)
            self.set_status(f'已加载：{os.path.basename(p)} ({img.shape[1]}x{img.shape[0]})')
        except Exception as e:
            self.set_status('加载图片出错: ' + str(e))

    @mainthread
    def update_display(self, bgr_img, overlay_mask=None):
        # Convert BGR to texture for Kivy Image
        if bgr_img is None:
            return
        rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        buf = rgb.flatten()
        tex = Texture.create(size=(w, h))
        tex.blit_buffer(buf.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        tex.flip_vertical()
        self.ids.img_display.texture = tex

    def set_status(self, txt):
        self.ids.status.text = '状态：' + txt

    def auto_process(self):
        if self.cv_img is None:
            self.set_status('请先打开图片')
            return
        self.set_status('正在自动检测掩膜（后台）...')
        Thread(target=self._auto_thread).start()

    def _auto_thread(self):
        try:
            img = self.cv_img.copy()
            mask = self._detect_mask_heuristic(img)
            # refine
            mask = self._refine_mask(mask)
            if mask.sum() == 0:
                self.set_status('未检测到显著水印，请手动绘制掩膜或提供模板')
                return
            self.mask = mask
            self.set_status('检测到掩膜，正在修复（inpaint）...')
            res = self._multi_inpaint(img, mask)
            self.result_img = res
            self.update_display(res)
            self.set_status('自动修补完成')
        except Exception as e:
            self.set_status('自动修复出错: ' + str(e))

    def toggle_paint_mode(self):
        if self.cv_img is None:
            self.set_status('请先打开图片')
            return
        self.paint_mode = not self.paint_mode
        if self.paint_mode:
            self.set_status('手动绘制掩膜：拖动绘制。再次点按钮退出并应用掩膜。')
            # bind events
            Window.bind(on_touch_down=self._on_touch_down)
            Window.bind(on_touch_move=self._on_touch_move)
            Window.bind(on_touch_up=self._on_touch_up)
        else:
            # unbind
            Window.unbind(on_touch_down=self._on_touch_down)
            Window.unbind(on_touch_move=self._on_touch_move)
            Window.unbind(on_touch_up=self._on_touch_up)
            # apply mask to img and preview
            if self.mask is not None and self.result_img is not None:
                self.set_status('应用手绘掩膜并修复（后台）...')
                Thread(target=self._apply_manual_inpaint).start()

    def _on_touch_down(self, window, touch):
        # simple test: only if touch near image area (we don't try to map coords perfectly)
        if not self.paint_mode:
            return False
        # approximate mapping: use image widget size & pos
        imgw = self.ids.img_display.width
        imgh = self.ids.img_display.height
        pos = self.ids.img_display.pos
        x_rel = (touch.x - pos[0]) / imgw
        y_rel = (touch.y - pos[1]) / imgh
        if x_rel < 0 or x_rel > 1 or y_rel < 0 or y_rel > 1:
            return False
        self._painting = True
        self._last = (x_rel, y_rel)
        self._paint_at(x_rel, y_rel)
        return True

    def _on_touch_move(self, window, touch):
        if not self.paint_mode or not self._painting:
            return False
        imgw = self.ids.img_display.width
        imgh = self.ids.img_display.height
        pos = self.ids.img_display.pos
        x_rel = (touch.x - pos[0]) / imgw
        y_rel = (touch.y - pos[1]) / imgh
        if x_rel < 0 or x_rel > 1 or y_rel < 0 or y_rel > 1:
            return False
        self._draw_line(self._last, (x_rel, y_rel))
        self._last = (x_rel, y_rel)
        return True

    def _on_touch_up(self, window, touch):
        if not self.paint_mode:
            return False
        self._painting = False
        self._last = None
        return True

    def _paint_at(self, x_rel, y_rel):
        h, w = self.cv_img.shape[:2]
        x = int(x_rel * w)
        y = int((1 - y_rel) * h)  # Kivy origin vs image origin
        cv2.circle(self.mask, (x, y), self.brush_size, 255, -1)
        # overlay preview on top of original
        preview = self.cv_img.copy()
        preview[self.mask==255] = (0,0,255)  # mark red for preview
        self.update_display(preview)

    def _draw_line(self, p1, p2):
        h, w = self.cv_img.shape[:2]
        x1 = int(p1[0] * w); y1 = int((1 - p1[1]) * h)
        x2 = int(p2[0] * w); y2 = int((1 - p2[1]) * h)
        cv2.line(self.mask, (x1, y1), (x2, y2), 255, int(self.brush_size*1.2))
        preview = self.cv_img.copy()
        preview[self.mask==255] = (0,0,255)
        self.update_display(preview)

    def _apply_manual_inpaint(self):
        try:
            res = self._multi_inpaint(self.cv_img.copy(), self.mask.copy())
            self.result_img = res
            self.update_display(res)
            self.set_status('手动修补完成')
        except Exception as e:
            self.set_status('手动修补错误: ' + str(e))

    def save_result(self):
        if self.result_img is None:
            self.set_status('没有可保存的结果')
            return
        # save to same directory as source or current dir
        outname = 'watermark_removed.png'
        try:
            # handle unicode paths: use imencode + write bytes
            _, buf = cv2.imencode('.png', self.result_img)
            with open(outname, 'wb') as f:
                f.write(buf.tobytes())
            self.set_status(f'已保存: {outname} （请在文件管理器中查找）')
        except Exception as e:
            self.set_status('保存失败: ' + str(e))

    # ---------- image processing utilities ----------
    def _detect_mask_heuristic(self, img):
        # fairly aggressive bright detection + adaptive threshold
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        _, th1 = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)
        th2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 31, -10)
        mask = cv2.bitwise_or(th1, th2)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        # keep components larger than threshold
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        cleaned = np.zeros_like(mask)
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] >= 80:
                cleaned[labels == i] = 255
        return cleaned

    def _refine_mask(self, mask):
        # open+close, dilation, blur threshold
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
        m = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        m = cv2.dilate(m, kernel, iterations=1)
        b = cv2.GaussianBlur(m, (9,9), 0)
        _, th = cv2.threshold(b, 10, 255, cv2.THRESH_BINARY)
        return th

    def _multi_inpaint(self, img, mask, method='telea', radii=(3,6,11)):
        flags = cv2.INPAINT_TELEA if method!='ns' else cv2.INPAINT_NS
        cur = img.copy()
        if mask.dtype != np.uint8:
            m = (mask>0).astype(np.uint8)*255
        else:
            m = mask
        for r in radii:
            try:
                cur = cv2.inpaint(cur, m, r, flags)
            except Exception:
                try:
                    cur = cv2.inpaint(cur, m, max(1, r//2), flags)
                except:
                    pass
        try:
            cur = cv2.bilateralFilter(cur, d=5, sigmaColor=75, sigmaSpace=75)
        except:
            pass
        # slight sharpen
        kernel_sharp = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
        try:
            cur = cv2.filter2D(cur, -1, kernel_sharp)
        except:
            pass
        return cur

class WatermarkRemoverApp(App):
    def build(self):
        self.title = 'Watermark Remover'
        root = Builder.load_string(KV)
        return root

if __name__ == '__main__':
    WatermarkRemoverApp().run()
