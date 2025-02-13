import os
import html
import datetime
import urllib.parse
import gradio as gr
from PIL import Image
from pathlib import Path
from typing import List, Tuple
import shutil
import json
import csv
from json import loads
import re
from modules import scripts
from scripts import promptgen as PG
from modules import cmd_args

extension_path = scripts.basedir()
refresh_symbol = '\U0001f504'  # 🔄
close_symbol = '\U0000274C'  # ❌
save_symbol = '\U0001F4BE' #💾
delete_style = '\U0001F5D1' #🗑️
clear_symbol = '\U0001F9F9' #🧹

card_size_value = 0
card_size_min = 0
card_size_max = 0
favourites = []
hideoldstyles = False
config_json = os.path.join(extension_path,"scripts" ,"config.json")

def save_card_def(value):
    global card_size_value
    save_settings("card_size",value)
    card_size_value = value
    
if not os.path.exists(config_json):
    default_config = {
        "card_size": 120,
        "card_size_min": 50,
        "card_size_max": 200,
        "autoconvert": True,
        "hide_old_styles": False,
        "favourites": []
    }
    
    with open(config_json, 'w') as config_file:
        json.dump(default_config, config_file, indent=4)

# Load values from the JSON file
with open(config_json, "r") as json_file:
    data = json.load(json_file)
    card_size_value = data["card_size"]
    card_size_min = data["card_size_min"]
    card_size_max = data["card_size_max"]
    autoconvert = data["autoconvert"]
    favourites = data["favourites"]
    hide_old_styles = data["hide_old_styles"]

def reload_favourites():
    with open(config_json, "r") as json_file:
        data = json.load(json_file)
        global favourites
        favourites = data["favourites"]

def save_settings(setting,value):
    with open(config_json, "r") as json_file:
        data = json.load(json_file)
    data[setting] = value
    with open(config_json, "w") as json_file:
        json.dump(data, json_file, indent=4)

def img_to_thumbnail(img):
    return gr.update(value=img)

character_translation_table = str.maketrans('"*/:<>?\\|\t\n\v\f\r', '＂＊／：＜＞？＼￨     ')
leading_space_or_dot_pattern = re.compile(r'^[\s.]')


def replace_illegal_filename_characters(input_filename: str):
    r"""
    Replace illegal characters with full-width variant
    if leading space or dot then add underscore prefix
    if input is blank then return underscore
    Table
    "           ->  uff02 full-width quotation mark         ＂
    *           ->  uff0a full-width asterisk               ＊
    /           ->  uff0f full-width solidus                ／
    :           ->  uff1a full-width colon                  ：
    <           ->  uff1c full-width less-than sign         ＜
    >           ->  uff1e full-width greater-than sign      ＞
    ?           ->  uff1f full-width question mark          ？
    \           ->  uff3c full-width reverse solidus        ＼
    |           ->  uffe8 half-width forms light vertical   ￨
    \t\n\v\f\r  ->  u0020 space
    """
    if input_filename:
        output_filename = input_filename.translate(character_translation_table)
        # if  leading character is a space or a dot, add _ in front
        return '_' + output_filename if re.match(leading_space_or_dot_pattern, output_filename) else output_filename
    return '_'  # if input is None or blank


def create_json_objects_from_csv(csv_file):
    json_objects = []
    with open(csv_file, 'r', newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Retrieve values from CSV with special character handling
            name = row.get('name', None)
            prompt = row.get('prompt', None)
            negative_prompt = row.get('negative_prompt', None)
            if name is None or prompt is None or negative_prompt is None:
                print("Warning: Skipping row with missing values.")
                continue
            safe_name = replace_illegal_filename_characters(name)
            json_data = {
                "name": safe_name,
                "description": "converted from csv",
                "preview": f"{safe_name}.jpg",
                "prompt": prompt,
                "negative": negative_prompt,
            }
            json_objects.append(json_data)
    return json_objects

def save_json_objects(json_objects):
    if not json_objects:
        print("Warning: No JSON objects to save.")
        return

    styles_dir = os.path.join(extension_path, "styles")
    csv_conversion_dir = os.path.join(styles_dir, "CSVConversion")
    os.makedirs(csv_conversion_dir, exist_ok=True)

    nopreview_image_path = os.path.join(extension_path, "nopreview.jpg")
    for json_obj in json_objects:
        try:
            json_file_path = os.path.join(csv_conversion_dir, f"{json_obj['name']}.json")
            with open(json_file_path, 'w') as jsonfile:
                json.dump(json_obj, jsonfile, indent=4)
            image_path = os.path.join(csv_conversion_dir, f"{json_obj['name']}.jpg")
            shutil.copy(nopreview_image_path, image_path)
        except Exception as e:
            print(f'{e}\nStylez Failed to convert {json_obj.get("name", str(json_obj))}')

        
if (autoconvert == True):
    csv_file_path = cmd_args.parser.parse_args().styles_file
    if os.path.exists(csv_file_path):
        json_objects = create_json_objects_from_csv(csv_file_path)
        save_json_objects(json_objects)
        save_settings("autoconvert", False)
    else:
        save_settings("autoconvert", False)


def generate_html_code():
    reload_favourites()
    style = None
    style_html = ""
    categories_list = ["All","Favourites"]
    save_categories_list =[]
    styles_dir = os.path.join(extension_path, "styles")
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime('%H:%M:%S.%f')
    formatted_time = formatted_time.replace(":", "")
    formatted_time = formatted_time.replace(".", "")
    try:
        for root, dirs, _ in os.walk(styles_dir):
            for directory in dirs:
                subfolder_name = os.path.basename(os.path.join(root, directory))
                if subfolder_name.lower() not in categories_list:
                    categories_list.append(subfolder_name)
                if subfolder_name.lower() not in save_categories_list:
                    save_categories_list.append(subfolder_name)    
        for root, _, files in os.walk(styles_dir):
            for filename in files:
                if filename.endswith(".json"):
                    json_file_path = os.path.join(root, filename)
                    subfolder_name = os.path.basename(root)
                    with open(json_file_path, "r", encoding="utf-8") as f:
                        try:
                            style = json.load(f)
                            title = style.get("name", "")
                            preview_image = style.get("preview", "")
                            description = style.get("description", "")
                            img = os.path.join(os.path.dirname(json_file_path), preview_image)
                            img = os.path.abspath(img)
                            prompt = style.get("prompt", "")
                            prompt = html.escape(json.dumps(prompt))
                            prompt_negative = style.get("negative", "")
                            prompt_negative =html.escape(json.dumps(prompt_negative))
                            imghack = img.replace("\\", "/")
                            json_file_path = json_file_path.replace("\\", "/")
                            encoded_filename = urllib.parse.quote(filename, safe="")
                            titlelower = str(title).lower()
                            color = ""
                            stylefavname =subfolder_name + "/" + filename
                            if (stylefavname in favourites):
                                color = "#EBD617"
                            else:
                                color = "#ffffff"
                            style_html += f"""
                            <div class="style_card" data-category='{subfolder_name}' data-title='{titlelower}' style="min-height:{card_size_value}px;max-height:{card_size_value}px;min-width:{card_size_value}px;max-width:{card_size_value}px;">
                                <img class="styles_thumbnail" src="{"file=" + img +"?timestamp"+ formatted_time}" alt="{title} Preview">
                                <div class="EditStyleJson">
                                    <button onclick="editStyle(`{title}`,`{imghack}`,`{description}`,`{prompt}`,`{prompt_negative}`,`{subfolder_name}`,`{encoded_filename}`,`Stylez`)">🖉</button>
                                </div>
                                <div class="favouriteStyleJson">
                                    <button class="favouriteStyleBtn" style="color:{color};" onclick="addFavourite('{subfolder_name}','{encoded_filename}', this)">★</button>
                                </div>
                                    <div onclick="applyStyle(`{prompt}`,`{prompt_negative}`,`Stylez`)" onmouseenter="event.stopPropagation(); hoverPreviewStyle(`{prompt}`,`{prompt_negative}`,`Stylez`)" onmouseleave="hoverPreviewStyleOut()" class="styles_overlay"></div>
                                    <div class="styles_title">{title}</div>
                                    <p class="styles_description">{description}</p>
                                </img>
                            </div>
                            """
                        except json.JSONDecodeError:
                            print(f"Error parsing JSON in file: {filename}")
                        except KeyError as e:
                            print(f"KeyError: {e} in file: {filename}")
    except FileNotFoundError:
        print("Directory '/models/styles' not found.")
    return style_html, categories_list, save_categories_list

def refresh_styles(cat):
    if cat is None or len(cat) == 0 or cat  == "[]" :
        cat = None
    newhtml = generate_html_code()
    newhtml_sendback = newhtml[0]
    newcat_sendback = newhtml[1]
    newfilecat_sendback = newhtml[2]
    return newhtml_sendback,gr.update(choices=newcat_sendback),gr.update(value="All"),gr.update(choices=newfilecat_sendback)

def save_style(title, img, description, prompt, prompt_negative, filename, save_folder):
    print(f"""Saved: '{save_folder}/{filename}'""")
    if save_folder and filename:
        if img is None or img == "":
            img = Image.open(os.path.join(extension_path, "nopreview.jpg")) 
        img = img.resize((200, 200))
        save_folder_path = os.path.join(extension_path, "styles", save_folder)
        if not os.path.exists(save_folder_path):
            os.makedirs(save_folder_path)
        json_data = {
            "name": title,
            "description": description,
            "preview": filename + ".jpg",
            "prompt": prompt,
            "negative": prompt_negative,
        }
        json_file_path = os.path.join(save_folder_path, filename + ".json")
        with open(json_file_path, "w") as json_file:
            json.dump(json_data, json_file, indent=4)
        img_path = os.path.join(save_folder_path, filename + ".jpg")
        img.save(img_path)
        msg = f"""File Saved to '{save_folder}'"""
        info(msg)
    else:
        msg = """Please provide a valid save folder and Filename"""
        warning(msg)
    return filename_check(save_folder,filename)

def info(message):
    gr.Info(message)

def warning(message):
    gr.Warning(message)
    
def tempfolderbox(dropdown):
    return gr.update(value=dropdown)

def filename_check(folder,filename):
    if filename is None or len(filename) == 0 :
        warning = """<p id="style_filename_check" style="color:red;">please add a file name</p>"""
    else:
        save_folder_path = os.path.join(extension_path, "styles", folder)
        json_file_path = os.path.join(save_folder_path, filename + ".json")
        if os.path.exists(json_file_path):
            warning = f"""<p id="style_filename_check" style="color:red;">Overwrite!! File Already Exists In '{folder}'</p>"""
        else:
            warning = """<p id="style_filename_check" style="color:green;">Filename Is Valid</p>"""
    return gr.update(value=warning)

def clear_style():
    previewimage = os.path.join(extension_path, "nopreview.jpg")
    return gr.update(value=None),gr.update(value=previewimage),gr.update(value=None),gr.update(value=None),gr.update(value=None),gr.update(value=None),gr.update(value=None)

def deletestyle(folder, filename):
    base_path = os.path.join(extension_path, "styles", folder)
    json_file_path = os.path.join(base_path, filename + ".json")
    jpg_file_path = os.path.join(base_path, filename + ".jpg")

    if os.path.exists(json_file_path):
        os.remove(json_file_path)
        warning(f"""Stlye "{filename}" deleted!! """)
        if os.path.exists(jpg_file_path):
            os.remove(jpg_file_path)
        else:
            warning(f"Error: {jpg_file_path} not found.")
    else:
        warning(f"Error: {json_file_path} not found.")

def addToFavourite(style):
 global favourites
 if (style not in favourites):
     favourites.append(style)
     save_settings("favourites",favourites)
     info("style added to favourites")

def removeFavourite(style):
 global favourites
 if (style in favourites):
     favourites.remove(style)
     save_settings("favourites",favourites)
     info("style removed from favourites")

def oldstyles(value):
    with open(config_json, "r") as json_file:
        data = json.load(json_file)
        if (data["hide_old_styles"] == True):
            save_settings("hide_old_styles",False)
        else:
            save_settings("hide_old_styles",True)

def generate_style(prompt,temperature,top_k,max_length,repitition_penalty,usecomma):
    result = PG.generate(prompt,temperature,top_k,max_length,repitition_penalty,usecomma)
    return gr.update(value=result)

class Stylez(scripts.Script):
    generate_styles_and_tags = generate_html_code()
    nopreview = os.path.join(extension_path, "nopreview.jpg")
    def title(self):
        return "Stylez"
    def ui(self, is_img2img):
        global hideoldstyles
        with gr.Tabs(elem_id = "Stylez"): 
            gr.HTML("""<div id="stylezPreviewBoxid" class="stylezPreviewBox"><p id="stylezPreviewPositive">test</p><p id="stylezPreviewNegative">test</p></div>""")
            with gr.TabItem(label="Styles",elem_id="styles_libary"):
                with gr.Column():
                    with gr.Column():
                        with gr.Tabs(elem_id = "libs"):

                            with gr.TabItem(label="Style Libary"):
                                with gr.Row():                      
                                    with gr.Column(elem_id="style_quicklist_column"):
                                        with gr.Row():
                                            gr.Text("QuickSave",show_label=False)
                                            with gr.Row():
                                                stylezquicksave_add = gr.Button("Add" ,elem_classes="stylezquicksave_add")
                                                stylezquicksave_clear = gr.Button("Clear" ,elem_classes="stylezquicksave_add")
                                        with gr.Row(elem_id="style_cards_row"):                        
                                                gr.HTML("""<ul id="styles_quicksave_list"></ul>""")
                                    with gr.Column():
                                        with gr.Row(elem_id="style_search_search"):
                                            Style_Search = gr.Textbox('', label="Searchbox", elem_id="style_search", placeholder="Search...", elem_classes="textbox", lines=1,scale=3)
                                            category_dropdown = gr.Dropdown(label="Category", choices=self.generate_styles_and_tags[1], value="All", lines=1, elem_id="style_Catagory", elem_classes="dropdown styles_dropdown",scale=1)
                                            refresh_button = gr.Button(refresh_symbol, label="Refresh", elem_id="style_refresh", elem_classes="tool", lines=1)
                                        with gr.Row():
                                            with gr.Column(elem_id="style_cards_column"):
                                                Styles_html=gr.HTML(self.generate_styles_and_tags[0])

                            with gr.TabItem(label="CivitAI"):
                                with gr.Row():
                                    with gr.Column(elem_id="civit_tags_column"):
                                        nsfwlvl = gr.Dropdown(label="NSFW:", choices=["None", "Soft", "Mature", "X"], value="None", lines=1, elem_id="civit_nsfwfilter", elem_classes="dropdown styles_dropdown",scale=1)
                                        sortcivit  = gr.Dropdown(label="Sort:", choices=["Most Reactions", "Most Comments", "Newest"], value="Most Reactions", lines=1, elem_id="civit_sortfilter", elem_classes="dropdown styles_dropdown",scale=1)
                                        periodcivit  = gr.Dropdown(label="Period:", choices=["AllTime", "Year", "Month", "Week", "Day"], value="AllTime", lines=1, elem_id="civit_periodfilter", elem_classes="dropdown styles_dropdown",scale=1)
                                    with gr.Column():
                                        with gr.Row(elem_id="style_search_search"):
                                            fdg = gr.Textbox('', label="Searchbox", elem_id="style_search", placeholder="DOES NOT WORK! NOT SUPPORTED BY API ", elem_classes="textbox", lines=1,scale=3)
                                            civitAI_refresh = gr.Button(refresh_symbol, label="Refresh", elem_id="style_refresh", elem_classes="tool", lines=1)
                                            pagenumber = gr.Number(label="Page:",value=1,minimum=1,visible=False)
                                        with gr.Row():
                                            with gr.Column(elem_id="civit_cards_column"):
                                                gr.HTML(f"""<div><div id="civitaiimages_loading"><p>Loading...</p></div><div onscroll="civitaiaCursorLoad(this)" id="civitai_cardholder" data-nopreview='{self.nopreview}'></div></div>""")

                            with gr.TabItem(label="Style Generator",elem_id="styles_generator"):
                                with gr.Row():
                                    with gr.Column():
                                        style_geninput_txt = gr.Textbox(label="Input:", lines=7,placeholder="Title goes here", elem_classes="stylez_promptgenbox")
                                        with gr.Row():
                                            style_gengrab_btn = gr.Button("Grab Current",elem_id="style_promptgengrab_btn")
                                    with gr.Column():
                                        style_genoutput_txt = gr.Textbox(label="Output:", lines=7,placeholder="Description goes here",elem_classes="stylez_promptgenbox")
                                        with gr.Row():
                                            style_gen_btn = gr.Button("Generate",elem_id="style_promptgen_btn")
                                            style_gensend_btn = gr.Button("Send to Prompt",elem_id="style_promptgen_send_btn")
                                with gr.Row():
                                    style_genusecomma_btn = gr.Checkbox(label="Use Commas", value=True)
                                with gr.Row():
                                    with gr.Column():
                                        style_gen_temp = gr.Slider(label="Temperature (Higher = More Diverse But Less Coherent): ", minimum=0.1, maximum=1.0 ,value=0.9)
                                        style_gen_top_k = gr.Slider(label="top_k (Number Of Tokens To Sample Per Step):", minimum=1, maximum=50 ,value=8,step=1)
                                    with gr.Column():
                                        style_max_length = gr.Slider(label="Maximum Number Of Tokens:", minimum=1, maximum=160 ,value=80,step=1)
                                        style_gen_repitition_penalty = gr.Slider(label="Repitition Penalty:", minimum=0.1, maximum=2 ,value=1.2,step=0.1)
                    with gr.Row(elem_id="stylesPreviewRow"):
                        gr.Checkbox(value=True,label="Apply/Remove Prompt", elem_id="styles_apply_prompt", elem_classes="styles_checkbox checkbox", lines=1)
                        gr.Checkbox(value=True,label="Apply/Remove Negative", elem_id="styles_apply_neg", elem_classes="styles_checkbox checkbox", lines=1)
                        gr.Checkbox(value=True,label="Hover Over Preview", elem_id="HoverOverStyle_preview", elem_classes="styles_checkbox checkbox", lines=1)
                        oldstylesCB = gr.Checkbox(value=hideoldstyles,label="Hide Styles Bar", elem_id="hide_default_styles", elem_classes="styles_checkbox checkbox", lines=1,interactive=True)
                        setattr(oldstylesCB,"do_not_save_to_config",True)
                        card_size_slider = gr.Slider(value=card_size_value,minimum=card_size_min,maximum=card_size_max,label="Size:", elem_id="card_thumb_size")
                        setattr(card_size_slider,"do_not_save_to_config",True)
                    with gr.Row(elem_id="stylesPreviewRow"):
                        favourite_temp = gr.Text(elem_id="favouriteTempTxt",interactive=False,label="Positive:",lines=2,visible=False)
                        add_favourite_btn = gr.Button(elem_id="stylezAddFavourite",visible=False)
                        remove_favourite_btn = gr.Button(elem_id="stylezRemoveFavourite",visible=False)
            with gr.TabItem(label="Style Editor",elem_id="styles_editor"):
                with gr.Row():
                    with gr.Column():
                        style_title_txt = gr.Textbox(label="Title:", lines=1,placeholder="Title goes here",elem_id="style_title_txt")
                        style_description_txt = gr.Textbox(label="Description:", lines=1,placeholder="Description goes here", elem_id="style_description_txt")
                        style_prompt_txt = gr.Textbox(label="Prompt:", lines=2,placeholder="Prompt goes here", elem_id="style_prompt_txt")
                        style_negative_txt = gr.Textbox(label="Negative:", lines=2,placeholder="Negative goes here", elem_id="style_negative_txt")
                    with gr.Column():
                        with gr.Row():
                            style_save_btn = gr.Button(save_symbol,label="Save Style", lines=1,elem_classes="tool", elem_id="style_save_btn")
                            style_clear_btn = gr.Button(clear_symbol,label="Clear", lines=1,elem_classes="tool" ,elem_id="style_clear_btn")
                            style_delete_btn = gr.Button(delete_style,label="Delete Style", lines=1,elem_classes="tool", elem_id="style_delete_btn")
                        thumbnailbox = gr.Image(value=None,label="Thumbnail (Please use 1:1 images):",elem_id="style_thumbnailbox",elem_classes="image",interactive=True,type='pil')
                        style_img_url_txt = gr.Text(label=None,lines=1,placeholder="Invisible textbox", elem_id="style_img_url_txt",visible=False)
                with gr.Row():
                    style_grab_current_btn = gr.Button("Grab Prompts",label="Grab Current", lines=1, elem_id="style_grab_current_btn")
                    style_lastgen_btn =gr.Button("Grab Last Generated Image",label="Save Style", lines=1,elem_id="style_lastgen_btn")
                with gr.Row():
                    with gr.Column():
                            style_filename_txt = gr.Textbox(label="Filename Name:", lines=1,placeholder="Filename", elem_id="style_filename_txt")
                            style_filname_check = gr.HTML("""<p id="style_filename_check" style="color:red;">Please Add a Filename</p>""",elem_id="style_filename_check_container")
                    with gr.Column():
                        with gr.Row():
                            style_savefolder_refrsh_btn = gr.Button(refresh_symbol, label="Refresh", lines=1,elem_classes="tool")
                            style_savefolder_txt = gr.Dropdown(label="Save Folder (Type To Create A New Folder):", value="Styles", lines=1, choices=self.generate_styles_and_tags[2], elem_id="style_savefolder_txt", elem_classes="dropdown",allow_custom_value=True)
                            style_savefolder_temp = gr.Textbox(label="Save Folder:", lines=1, elem_id="style_savefolder_temp",visible=False)
        civitAI_refresh.click(fn=None,_js="refreshfetchCivitai",inputs=[nsfwlvl,sortcivit,periodcivit])
        periodcivit.change(fn=None,_js="refreshfetchCivitai",inputs=[nsfwlvl,sortcivit,periodcivit])
        sortcivit.change(fn=None,_js="refreshfetchCivitai",inputs=[nsfwlvl,sortcivit,periodcivit])
        nsfwlvl.change(fn=None,_js="refreshfetchCivitai",inputs=[nsfwlvl,sortcivit,periodcivit])
        style_gengrab_btn.click(fn=None,_js="stylesgrabprompt" ,outputs=[style_geninput_txt])
        style_gensend_btn.click(fn=None,_js='sendToPromtbox',inputs=[style_genoutput_txt])
        style_gen_btn.click(fn=generate_style,inputs=[style_geninput_txt,style_gen_temp,style_gen_top_k,style_max_length,style_gen_repitition_penalty,style_genusecomma_btn],outputs=[style_genoutput_txt])
        oldstylesCB.change(fn=oldstyles,inputs=[oldstylesCB],_js="hideOldStyles")
        refresh_button.click(fn=refresh_styles,inputs=[category_dropdown], outputs=[Styles_html,category_dropdown,category_dropdown,style_savefolder_txt])
        card_size_slider.release(fn=save_card_def,inputs=[card_size_slider])
        card_size_slider.change(fn=None,inputs=[card_size_slider],_js="cardSizeChange")
        category_dropdown.change(fn=None,_js="filterSearch",inputs=[category_dropdown,Style_Search])
        Style_Search.change(fn=None,_js="filterSearch",inputs=[category_dropdown,Style_Search])
        style_img_url_txt.change(fn=img_to_thumbnail, inputs=[style_img_url_txt],outputs=[thumbnailbox])
        style_grab_current_btn.click(fn=None,_js='grabCurrentSettings')
        style_lastgen_btn.click(fn=None,_js='grabLastGeneratedimage')
        style_savefolder_refrsh_btn.click(fn=refresh_styles,inputs=[category_dropdown], outputs=[Styles_html,category_dropdown,category_dropdown,style_savefolder_txt])
        style_save_btn.click(fn=save_style, inputs=[style_title_txt, thumbnailbox, style_description_txt,style_prompt_txt, style_negative_txt, style_filename_txt, style_savefolder_temp], outputs=[style_filname_check])
        style_filename_txt.change(fn=filename_check, inputs=[style_savefolder_temp,style_filename_txt], outputs=[style_filname_check])
        style_savefolder_txt.change(fn=tempfolderbox, inputs=[style_savefolder_txt], outputs=[style_savefolder_temp])
        style_savefolder_temp.change(fn=filename_check, inputs=[style_savefolder_temp,style_filename_txt], outputs=[style_filname_check])
        style_clear_btn.click(fn=clear_style, outputs=[style_title_txt,style_img_url_txt,thumbnailbox,style_description_txt,style_prompt_txt,style_negative_txt,style_filename_txt])
        style_delete_btn.click(fn=deletestyle, inputs=[style_savefolder_temp,style_filename_txt])
        add_favourite_btn.click(fn=addToFavourite, inputs=[favourite_temp])
        remove_favourite_btn.click(fn=removeFavourite, inputs=[favourite_temp])
        stylezquicksave_add.click(fn=None,_js="addQuicksave")
        stylezquicksave_clear.click(fn=None,_js="clearquicklist")
