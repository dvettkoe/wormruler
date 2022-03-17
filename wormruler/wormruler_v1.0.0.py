from os import walk
from os.path import join, basename, exists
from cv2 import selectROI, imshow, destroyWindow
from pandas import DataFrame, concat, ExcelWriter
from imageio import get_reader, get_writer

from skimage.morphology import thin, remove_small_holes, remove_small_objects, closing
from skimage.util import img_as_ubyte, img_as_bool
from skimage.filters import threshold_otsu
from skimage.util import invert
from skimage import color

from fil_finder import FilFinder2D
from astropy.units import pix, pc

from warnings import filterwarnings
from tkinter import filedialog, messagebox, Button, Label, Entry, StringVar, Checkbutton, IntVar, Tk, Toplevel
from tkinter.font import Font
from tkinter.ttk import Button as tButton
from tkinter.ttk import Separator, Progressbar

#from time import process_time


"""
-----
WormRuler by Marius Seidenthal and Dennis Vettkötter

Changelog:
Version 0.1.0 (Seidenthal)
- original script written
Version 0.1.1 (Vettkötter)
- GUI added
Version 0.2.0 (Seidenthal)
- Included Entry field for Gamma values
Version 0.2.1 (Vettkötter)
- Included new button "Start all" for batch processing
Version 0.3.0 (Vettkötter)
- Improved skeletonization: Removed branches in skeletons
Version 0.3.1 (Vettkötter)
- Skeletonization step of v3 resulted in too short GIFs if only black images
  appeared in black&white GIFs:
    - Removed suppress Exception with try and except lines
Version 0.4.0 (Vettkötter + Seidenthal)
- Removed skan from skeletonize function
- Raw length values (in pixel) will be saved in separate textfile "*_raw_lengths.txt"
- Added separate normalize function to load raw lengths data from skeletonize step 
  - normalizes lengths to data before pulsestart
  - new normalize function will be started directly after skeletonize step (no additional GUI interface included)
Version 0.4.1 (Vettkötter)
- Added GUI option to start normalization on its own.
Version 0.4.2 (Seidenthal)
- Added .mov/.MOV support
Version 0.4.3 (Vettkötter)
- Added file name to final results table as column name for each worm
Version 0.5.0 (Vettkötter)
- Added input field to ask whether user will override existing skeleton files or skip to unskeletonized files.
Version 0.5.1 (Seidenthal + Vettkötter)
- Added input of framerate to GUI
Version 1.0.0 (Seidenthal + Vettkötter)
- Adjusted changelog information
- publishing first WormRuler version on GitHub
-----
"""

# GUI window
gui = Tk()
gui.geometry('340x540')
gui.title("WormRuler")
gui.iconbitmap('wormruler_ico.ico')

# Ignore warnings
filterwarnings('ignore', '.*No beam width given.*', )
filterwarnings('ignore', '.*Graph pruning reached max iterations.*', )

# WormRuler code

# Function to crop video according to ROI which ist needed if round field of view is used
def crop_center(img, cropx, cropy):
    y, x = img.shape
    startx = x // 2 - (cropx // 2)
    starty = y // 2 - (cropy // 2)
    return img[starty:starty + cropy, startx:startx + cropx]


# substracts background and writes binary gif file
def background_correction():
    bw_done.grid_remove()
    print("Background correction started... \n")

    Gamma_value = gamma.get()
    if Gamma_value == "":
        messagebox.showerror("Error", "Please enter Gamma value.\nShould be approximately between 0.7 and 1.3.")
    else:
        # open vid
        Gamma_value = float(Gamma_value)
        video_root = video_path.get() + "/"

        # find all subfolders which are labeled according to the measurement conditions
        folders = []
        for r, d, f in walk(video_root):
            for folder in d:
                folders.append(folder)
        print("Following conditions found: " + str(folders) + "\n")

        progress_bw_value = 0
        progress_bw_list = []
        for r, d, f in walk(str(video_root)):
            for file in f:
                if ".AVI" in file or ".avi" in file or ".mov" in file or ".MOV" in file:
                    progress_bw_list.append(file)
        progress_bw_steps = 100 / len(progress_bw_list)

        for folder in folders:
            print("Background correction of condition " + "\"" + folder + "\":")

            # find all videos in the respective folder
            video_paths = []
            for r, d, f in walk(str(video_root) + "/" + str(folder)):
                for file in f:
                    if ".AVI" in file or ".avi" in file or ".mov" in file or ".MOV" in file:
                        video_paths.append(join(r, file))
            for v_path in video_paths:
                print(v_path)
                vid = get_reader(v_path, 'ffmpeg')

                with get_writer(v_path[:-4] + "_bw.gif", mode='I', fps=int(framerate.get())) as writer:
                    # get frames
                    for num, image in enumerate(vid):
                        # convert to grayscale
                        img = color.rgb2gray(image)

                        # get threshold and make binary
                        otsu = threshold_otsu(img)
                        binary = img > otsu * Gamma_value
                        binary = invert(binary)
                        # close holes, remove small objects
                        binary = remove_small_objects(binary, min_size=2000)
                        binary = closing(binary)
                        binary = remove_small_holes(binary, area_threshold=700)
                        # write image to file
                        binary = img_as_ubyte(binary)
                        writer.append_data(binary)

                    progress_bw_value += progress_bw_steps
                    progressbar_bw['value'] = progress_bw_value
                    progressbar_bw.update()

            print("\n")
        bw_done.grid(row=6, column=1, sticky='w', padx=200)
        print("Background correction complete!")
        print("Ready for skeletonization.")


# create ROI to remove edges, write ROI coordinates to text file, make new for each day of measurement
# simply draw ROI over whole image if the field of view is rectengular

def ROI_set():
    print("\nSelect ROI for skeletonization!\n")
    # open vid
    video_root = video_path.get() + "/"
    root_name = basename(video_path.get())
    folders = []
    for r, d, f in walk(video_root):
        for folder in d:
            folders.append(folder)

    video_paths = []
    for r, d, f in walk(str(video_root) + "/" + str(folders[0])):
        for file in f:
            if "_bw.gif" in file:
                video_paths.append(join(r, file))
    # read first video and set ROI
    vid1 = get_reader(video_paths[0], 'ffmpeg')
    for frame in vid1:
        fromCenter = False
        roi = selectROI(frame, fromCenter)
        imCrop = frame[int(roi[1]):int(roi[1] + roi[3]), int(roi[0]):int(roi[0] + roi[2])]
        imshow("ROI", imCrop)
        textfile = open(video_root + str(root_name) + "_ROI.txt", "w")
        textfile.write('\n'.join(str(s) for s in roi))

        textfile.close()
        destroyWindow('ROI selector')
        destroyWindow('ROI')
        break


# takes background corrected gifs and crops them using the predefined ROI
# makes skeleton of worms and writes them to new gif
# analyzes length of skeleton and stores values in textfile for each worm
def skeletonize():

    print("ROI selected. Starting skeletonization...")
    # open vid
    video_root = video_path.get() + "/"
    progress_skel_value = 0
    progress_skel_list = []
    if check.get() == 1:
        for r, d, f in walk(str(video_root)):
            for file in f:
                if "_bw.gif" in file:
                    progress_skel_list.append(file)
        progress_skel_steps = 100 / len(progress_skel_list)
    else:
        for r, d, f in walk(str(video_root)):
            for file in f:
                if "_bw.gif" in file:
                    if exists(join(r, file[:-7]) + "_raw_lengths.txt"):
                        pass
                    else:
                        progress_skel_list.append(file)
        if len(progress_skel_list) == 0:
            print("\nAll files skeletonized! Check override or proceed to normalization!\n")
        else:
            progress_skel_steps = 100 / len(progress_skel_list)

    folders = []
    for r, d, f in walk(video_root):
        for folder in d:
            folders.append(folder)

    print("Following conditions found: " + str(folders) + "\n")

    # get roi from txtfile
    roi_file = []
    for r, d, f in walk(video_root):
        for file in f:
            if file.endswith("_ROI.txt"):
                roi_file.append(join(r, file))
    textfile = open(roi_file[0], "r")
    lines = textfile.readlines()
    roi = []
    for line in lines:
        line.strip(r"\n")
        roi.append(int(line))
    textfile.close()

    for folder in folders:
        print("Skeletonizing condition " + "\"" + folder + "\":")

        video_paths = []
        if check.get() == 1:
            for r, d, f in walk(str(video_root) + "/" + str(folder)):
                for file in f:
                    if "_bw.gif" in file:
                        video_paths.append(join(r, file))
        else:
            for r, d, f in walk(str(video_root) + "/" + str(folder)):
                for file in f:
                    if "_bw.gif" in file:
                        if exists(join(r, file[:-7]) + "_raw_lengths.txt"):
                            pass
                        else:
                            video_paths.append(join(r, file))

        for v_path in video_paths:
            print(v_path)
            vid = get_reader(v_path, 'ffmpeg')
            # get frames
            skel_txt = open(v_path[:-7] + "_raw_lengths.txt", "w")

            with get_writer(v_path[:-7] + "_skel.gif", mode='I', fps=int(framerate.get())) as writer:
                for num, frame in enumerate(vid):
                    img = color.rgb2gray(frame)
                    # crop image
                    a, b, c, d = roi
                    img_crop = img[int(b):int(b + d), int(a):int(a + c)]
                    binary = img_as_bool(img_crop)
                    skel = thin(binary)
                    try:
                        fil = FilFinder2D(skel, distance=250 * pc, mask=skel)
                        fil.medskel(verbose=False)
                        fil.analyze_skeletons(branch_thresh=5 * pix, skel_thresh=10 * pix, prune_criteria='length')
                        skel_fil = fil.skeleton_longpath
                        skel_length = fil.lengths()
                        skel_str = str(skel_length)
                        skel_num = skel_str[1:-5]
                        skel_list = skel_num.split("  ")
                        skel_list2 = ' '.join(skel_list).split()
                        skel_floats = [float(x) for x in skel_list2]
                        skel_floats.sort(reverse=True)
                        if len(skel_floats) == 1:
                            skel_txt.write(str(skel_floats[0]) + "\n")
                        elif len(skel_floats) == 2:
                            combined = skel_floats[0] + skel_floats[1]
                            skel_txt.write(str(combined) + "\n")
                        else:
                            skel_txt.write("None" + "\n")
                        skel_fil_gif = img_as_ubyte(skel_fil)
                        writer.append_data(skel_fil_gif)
                    except:
                        skel_txt.write("None" + "\n")
            skel_txt.close()
            progress_skel_value += progress_skel_steps
            progressbar_skel['value'] = progress_skel_value
            progressbar_skel.update()

        print("\n")
    skel_done.grid(row=10, column=1, sticky='w', padx=200)
    print("Skeletonization complete.")
    print("Ready for normalization.\n")



# normalizes bodylengths to predefined pulsestart
# writes normalized bodylengths to textfile for each worm
def normalize():
    print("Starting normalization...\n")
    # open vid
    video_root = video_path.get() + "/"
    pulsestart_f = pulse_start.get()
    if pulsestart_f == "":
        messagebox.showerror("Error", "Please enter start of light pulse (in seconds)")
    else:
        pulsestart_s = int(pulse_start.get())
        print("Pulse started after " + str(pulsestart_s) + "s")
        pulsestart_f = pulsestart_s * int(framerate.get())
        print("(or after " + str(pulsestart_f) + " frames!)\n")

        normalize_done.grid_remove()
        progress_norm_value = 0
        progress_norm_list = []
        for r, d, f in walk(str(video_root)):
            for file in f:
                if "_bw.gif" in file:
                    progress_norm_list.append(file)
        progress_norm_steps = 100 / len(progress_norm_list)

        folders = []
        for r, d, f in walk(video_root):
            for folder in d:
                folders.append(folder)

        print("Following conditions found: " + str(folders) + "\n")

        for folder in folders:
            print("Normalize skeleton data for condition " + "\"" + folder + "\":")

            text_paths = []
            for r, d, f in walk(str(video_root) + "/" + str(folder)):
                for file in f:
                    if "_raw_lengths.txt" in file:
                        text_paths.append(join(r, file))

            for text_path in text_paths:
                print(text_path)
                file = open(text_path, "r")
                lines = file.readlines()
                body_lengths = []
                for body_length in lines:
                    length = body_length.rstrip("\n")
                    if length == "None":
                        body_lengths.append(None)
                    else:
                        body_lengths.append(float(length))

                list_tillpulsestart = []
                for worm in body_lengths[5:pulsestart_f - 1]:
                    # remove None values
                    if worm:
                        list_tillpulsestart.append(worm)

                # check if worm before pulse is usable for normalization
                if len(list_tillpulsestart) != 0:
                    # get average before pulse
                    average_before_pulse = sum(list_tillpulsestart) / len(list_tillpulsestart)

                    # normalization
                    bodylength_norm = []
                    for value in body_lengths:
                        if value:
                            value_norm = value / average_before_pulse
                            # remove values above 1.2 and below 0.8
                            if 0.8 < value_norm < 1.2:
                                bodylength_norm.append(value_norm)
                            else:
                                bodylength_norm.append(None)
                        else:
                            bodylength_norm.append(None)

                    # writes bodylengths to textfiles
                    textfile = open(text_path[:-16] + "_data.txt", "w")
                    for element in bodylength_norm:
                        textfile.write(str(element) + "\n")
                    textfile.close()
                else:
                    print("Error found for " + text_path)
                    print("Please check if gamma value was adjusted correctly!\n")

                progress_norm_value += progress_norm_steps
                progressbar_normalize['value'] = progress_norm_value
                progressbar_normalize.update()
            normalize_done.grid(row=14, column=1, sticky='w', padx=200)
            print("Ready for data analyis.")


# Combining functions roi_set, skeletonize and normalization
def skeletonization():
    skel_done.grid_remove()
    video_root = video_path.get() + "/"
    root_name = basename(video_path.get())
    if exists(video_root + str(root_name) + "_ROI.txt"):
        skeletonize()
    else:
        ROI_set()
        skeletonize()

# takes textfiles containing normalized bodylengths and writes them to excelfile
# calculates mean, sem and N
def data_analyis():
    data_done.grid_remove()
    print("\nData Analysis started...")
    video_root = video_path.get() + "/"

    progress_data_value = 0
    progress_data_list = []

    folders = []
    for r, d, f in walk(video_root):
        for folder in d:
            folders.append(folder)
            progress_data_list.append(folder)
    progress_data_steps = 100 / len(progress_data_list)
    print("Following conditions found: " + str(folders) + "\n")

    for folder in folders:
        print("Analyze data for condition " + "\"" + folder + "\":")
        # get textfiles with normalized bodylengths
        text_paths = []
        file_names = []
        for r, d, f in walk(str(video_root) + "/" + str(folder)):
            for file in f:
                if "_data.txt" in file:
                    text_paths.append(join(r, file))
                    file_names.append(file[:-9])
        body_lengths_list = []

        print(file_names)
        for text_path in text_paths:
            print(text_path)
            file = open(text_path, "r")
            lines = file.readlines()
            body_lengths = []
            for body_length in lines:
                length = body_length.rstrip("\n")
                if length == "None":
                    body_lengths.append(None)
                else:
                    body_lengths.append(float(length))
            body_lengths_list.append(body_lengths)

        df = DataFrame(body_lengths_list)
        df = DataFrame.transpose(df)
        mean = df.mean(axis=1, skipna=True)
        sem = df.sem(axis=1, skipna=True)
        n = df.count(axis=1)
        df_final = concat([df, mean, sem, n], axis=1)
        column_names = [str(x) for x in file_names]
        column_names.append("Mean")
        column_names.append("SEM")
        column_names.append("n")
        df_final.columns = [column_names]
        with ExcelWriter(video_root + "/" + folder + "/" + folder + "_results.xlsx") as writer:
            df_final.to_excel(writer, sheet_name=folder, engine='openpyxl')
        print("Results written as: " + str(video_root) + str(folder) + "_results.xlsx")
        print("\n")

        progress_data_value += progress_data_steps
        progressbar_data['value'] = progress_data_value
        progressbar_data.update()

    data_done.grid(row=17, column=1, sticky='w', padx=200)
    print("Data analysis complete.")
    print("Go and turn your data into beautiful graphs!")


def run_all():
    print("WormRuler - \"Run all\" function started:")
    # open vid
    folders = []
    video_root = video_path.get() + "/"
    root_name = basename(video_path.get())
    pulsestart_f = pulse_start.get()
    Gamma_value = gamma.get()
    if Gamma_value == "":
        messagebox.showerror("Error", "Please enter Gamma value.\nShould be approximately between 0.7 and 1.3.")
    else:
        if pulsestart_f == "":
            messagebox.showerror("Error", "Please enter start of light pulse (in seconds).")
        else:
            if exists(video_root + str(root_name) + "_ROI.txt"):
                background_correction()
                skeletonize()
                normalize()
                data_analyis()
            else:
                print("\nSelect ROI for skeletonization first!\n")
                for r, d, f in walk(video_root):
                    for folder in d:
                        folders.append(folder)

                video_paths = []
                for r, d, f in walk(str(video_root) + "/" + str(folders[0])):
                    for file in f:
                        if ".AVI" in file or ".avi" in file or ".mov" in file or ".MOV" in file:
                            video_paths.append(join(r, file))
                # read first video and set ROI
                vid1 = get_reader(video_paths[0], 'ffmpeg')
                for frame in vid1:
                    fromCenter = False
                    roi = selectROI(frame, fromCenter)
                    imCrop = frame[int(roi[1]):int(roi[1] + roi[3]), int(roi[0]):int(roi[0] + roi[2])]
                    imshow("ROI", imCrop)
                    textfile = open(video_root + str(root_name) + "_ROI.txt", "w")
                    textfile.write('\n'.join(str(s) for s in roi))

                    textfile.close()
                    destroyWindow('ROI selector')
                    destroyWindow('ROI')
                    break
                background_correction()
                skeletonize()
                normalize()
                data_analyis()


def close():
    gui.destroy()


# Get path functions
def getvideo_path():
    video_selected = filedialog.askdirectory(title="Select directory of raw videos")
    video_path.set(video_selected)


# Tooltip code
class ToolTip(object):

    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        """Display text in tooltip window"""
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 57
        y = y + cy + self.widget.winfo_rooty() + 27
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = Label(tw, text=self.text, justify="left",
                         background="#ffffe0", relief="solid", borderwidth=1,
                         font=("tahoma", "10", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


def CreateToolTip(widget, text):
    toolTip = ToolTip(widget)

    def enter(event):
        toolTip.showtip(text)

    def leave(event):
        toolTip.hidetip()

    widget.bind('<Enter>', enter)
    widget.bind('<Leave>', leave)


# GUI setup


# GUI font styles
myFont = Font(family='Cambria', size=10, weight="bold")
titleFont = Font(family='Cambria', size=20, weight="bold")
fileFont = Font(size=9, weight="bold")

# Title
gui_title = Label(gui, text="WormRuler", font=titleFont)
gui_title.grid(row=1, column=1, pady=15, sticky='w', padx=70)

border_label = Label(gui, text="   ")
border_label.grid(row=2, column=0, sticky="w")

# Path selection
video_path = StringVar()
path_label = Label(gui, text="Path")
path_label.grid(row=2, column=1, sticky="w")
path_entry = Entry(gui, textvariable=video_path, width=28)
path_entry.grid(row=2, column=1, sticky='w', padx=30)
btn_path_entry = tButton(gui, text="Browse", command=getvideo_path)
btn_path_entry.grid(row=2, column=1, sticky='w', padx=210)

# Path selection info button
path_info = "Browse to folder with original videos.\n\n" \
            "Optional:\n \"To merge experiments from different\n" \
            " days, create a new folder with sub-\n" \
            " folders for each condition to be merged.\n" \
            " Copy all *_bw_data.txt from each condition\n" \
            " into this new folder.\n" \
            " Select this folder path and run \"Analyze Data\" again!\""

path_infobutton = Button(gui, text='i', font=myFont,
                            bg='white', fg='blue', bd=0)
CreateToolTip(path_infobutton, text=path_info)
path_infobutton.grid(row=2, column=1, padx=290)

# GUI Separator background correction
Separator(gui, orient="horizontal").grid(row=3, column=0, columnspan=2, sticky='ew', pady=5)

# background correction GUI

gamma = StringVar()

gamma_label = Label(gui, text="Gamma:          ")
gamma_label.grid(row=5, column=1, sticky="w")
gamma_entry = Entry(gui, textvariable=gamma, width=3)
gamma_entry.grid(row=5, column=1, pady=5, padx=68, sticky='w')

# Gamma info button
gamma_info = "Enter Gamma value depending on the brightness of the videos.\n" \
             "Should be approximately between 0.7 and 1.3."

gamma_infobutton = Button(gui, text='i', font=myFont,
                             bg='white', fg='blue', bd=0)
CreateToolTip(gamma_infobutton, text=gamma_info)
gamma_infobutton.grid(row=5, column=1, padx=290)

bg_title = Label(gui, text="Background Correction", font=myFont)
bg_title.grid(row=4, column=1, pady=10, sticky='w')

btn_bg_start = tButton(gui, text="Start", command=background_correction)
btn_bg_start.grid(row=6, column=1, sticky='w')

progressbar_bw = Progressbar(gui, length=100)
progressbar_bw.grid(row=6, column=1, sticky='w', padx=90)

bw_done = Label(gui, text="Done!", font=fileFont)

# GUI Separator skeletonize
Separator(gui, orient="horizontal").grid(row=7, column=0, columnspan=2, sticky='ew', pady=5)

# skeletonize GUI
skel_title = Label(gui, text="Skeletonize", font=myFont)
skel_title.grid(row=9, column=1, pady=5, sticky='w')

# Check info button
check_info = "Keep unchecked if starting WormRuler for the first time.\n\n" \
            "Unchecked:\n Skeletonization step will ignore videos" \
            " already skeletonized.\n" \
            " Can be useful if program was stopped in between.\n" \
            " Consider deleting last \"*_raw_lengths.txt\"" \
            " in folder.\n" \
            "Checked:\n Skeletonization will be done for all videos.\n" \
             " Can be useful if gamma value needed to be adjusted."

check_infobutton = Button(gui, text='i', font=myFont,
                            bg='white', fg='blue', bd=0)
CreateToolTip(check_infobutton, text=check_info)
check_infobutton.grid(row=9, column=1, padx=290)
check = IntVar()
skel_check = Checkbutton(gui, text="(Override existing skeletons)", variable=check)
skel_check.grid(row=9, column=1, sticky='w', padx=90)

framerate = StringVar()
framerate.set("30")

framerate_label = Label(gui, text= "Framerate:           (fps)")
framerate_label.grid(row=10, column=1, sticky="w")
framerate_entry = Entry(gui, textvariable=framerate, width=3)
framerate_entry.grid(row=10, column=1, pady=5, padx=68, sticky='w')

btn_skel_start = tButton(gui, text="Start", command=skeletonization)
btn_skel_start.grid(row=11, column=1, sticky="w")

progressbar_skel = Progressbar(gui, length=100)
progressbar_skel.grid(row=11, column=1, sticky='w', padx=90)

skel_done = Label(gui, text="Done!", font=fileFont)

# GUI Separator normalize data
Separator(gui, orient="horizontal").grid(row=12, column=0, columnspan=2, sticky='ew', pady=5)

# Normalize Data GUI
normalize_title = Label(gui, text="Normalize Data", font=myFont)
normalize_title.grid(row=13, column=1, pady=10, sticky='w')

pulse_start = StringVar()

pulse_label = Label(gui, text="Pulse-start:          (s)")
pulse_label.grid(row=14, column=1, sticky="w")
pulse_entry = Entry(gui, textvariable=pulse_start, width=3)
pulse_entry.grid(row=14, column=1, pady=5, padx=68, sticky='w')


btn_normalize_start = tButton(gui, text="Normalize", command=normalize)
btn_normalize_start.grid(row=15, column=1, sticky='w')

progressbar_normalize = Progressbar(gui, length=100)
progressbar_normalize.grid(row=15, column=1, sticky='w', padx=90)

normalize_done = Label(gui, text="Done!", font=fileFont)

# GUI Separator analyze data
Separator(gui, orient="horizontal").grid(row=16, column=0, columnspan=2, sticky='ew', pady=5)

# Analyze Data GUI
data_title = Label(gui, text="Analyze Data", font=myFont)
data_title.grid(row=17, column=1, pady=10, sticky='w')

btn_data_start = tButton(gui, text="Analyze", command=data_analyis)
btn_data_start.grid(row=18, column=1, sticky='w')

progressbar_data = Progressbar(gui, length=100)
progressbar_data.grid(row=18, column=1, sticky='w', padx=90)

data_done = Label(gui, text="Done!", font=fileFont)

# GUI Separator all and close buttons
Separator(gui, orient="horizontal").grid(row=19, column=0, columnspan=2, sticky='ew', pady=10)

# GUI All-in-one button
btn_all = Button(gui, text="Start all",
                    relief='groove', activebackground='#99ccff',
                    command=run_all)
btn_all.grid(row=20, column=1, padx=90, sticky="w")

# GUI Close Window Button
btn_close = Button(gui, text="Close",
                      bg='#ff6666', relief='groove',
                      command=close)
btn_close.grid(row=20, column=1, padx=150, sticky="w")

# GUI window loop
gui.mainloop()
