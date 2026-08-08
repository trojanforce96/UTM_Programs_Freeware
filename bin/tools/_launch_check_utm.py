"""Launch UTM lecturer wizard briefly — compare to EA."""
import os
import sys

os.chdir(r"d:\EA_ASCII")
os.environ["EA_EDITION"] = "lecturer"
os.environ["EA_LECTURER"] = "1"
sys.path.insert(0, os.path.join(os.getcwd(), "bin"))

import utm_coordinate_wizard as cw  # noqa: E402

print("=== UTM lecturer bat launch check ===")
print("script:", os.path.abspath(cw.__file__))
print("LECTURER_MODE:", cw.LECTURER_MODE)
print("app_name():", cw.app_name())

app = cw.CassiniApp()
print("window title:", app.title())
print("header label:", app._hdr_title_lbl.cget("text"))
if getattr(app, "_hdr_sub_lbl", None):
    print("header sub:", app._hdr_sub_lbl.cget("text"))
from app_paths import resource as res
print("logo path:", res("logo.png"))
tabs = []
nb = [w for w in app.winfo_children() if w.winfo_class() == "TNotebook"]
if nb:
    for tab_id in nb[0].tabs():
        tabs.append(nb[0].tab(tab_id, "text").strip())
print("tabs:", tabs)

app.after(300, app.destroy)
app.mainloop()
