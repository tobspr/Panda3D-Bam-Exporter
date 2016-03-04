from __future__ import print_function


# Enter the path to the render pipeline here, without trailing slash
RP_PATH = "E:/Projects/Brainz stuff/RenderPipeline"



import sys
import os
from panda3d.core import *
from direct.showbase.ShowBase import ShowBase

base_path = os.path.dirname(os.path.realpath(__file__))
out_path = os.path.join(base_path, "output.png")
out_fpath = Filename.from_os_specific(out_path)

try:
    w = int(sys.argv[1])
    h = int(sys.argv[2])
except:
    print("Invalid window size! Using 512 x 512")
    w, h = 512, 512

# Make sure the sizes are multiples of 4
w = w + 4 - w % 4
h = h + 4 - h % 4

rp_fpath = Filename.from_os_specific(RP_PATH)

sys.path.insert(0, RP_PATH)

from rpcore import RenderPipeline

class MainBase(ShowBase):

    def __init__(self):

        load_prc_file_data("", "win-size {} {}".format(w, h))
        load_prc_file_data("", "window-type offscreen")

        self.rp = RenderPipeline(self)
        self.rp.load_settings(
            os.path.join(base_path, "pipeline.yaml"))
        self.rp.set_empty_loading_screen()
        self.rp.create()

        self.rp.daytime_mgr.time = 0.45

        model = loader.loadModel("preview.bam")
        model.reparent_to(render)
        model.set_two_sided(True)
        self.rp.prepare_scene(model)

        base.disable_mouse()
        base.camLens.set_fov(110)

        base.render2d.hide()
        base.pixel2d.hide()
        base.pixel2dp.hide()

        main_cam = model.find("**/Camera")
        if main_cam:
            transform_mat = main_cam.get_transform(render).get_mat()
            transform_mat = Mat4.convert_mat(CS_zup_right, CS_yup_right) * transform_mat
            base.camera.set_mat(transform_mat)
        else:
            print("WARNING: No camera found")

app = MainBase()
for i in range(60):
    taskMgr.step()
    base.graphicsEngine.render_frame()

base.win.save_screenshot(out_fpath)
