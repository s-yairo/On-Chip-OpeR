import base64
import html
import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core.ai import AIConnector
from core.experiment_records import (
    PROCESS_STATUS_OPTIONS,
    RESULT_STATUS_OPTIONS,
    add_experiment_record,
    create_experiment_record,
    load_experiment_records,
    save_experiment_records,
    update_experiment_record,
)
from core.experiment_condition_advisor import render as render_experiment_condition_advisor_page
from core.product_catalog import (
    build_product_name_index,
    filter_products,
    find_droplet_product_candidates,
    find_product_name_spans,
    load_product_catalog,
    product_count,
    device_compatibility_categories,
)

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "manual_steps.json"
PRODUCT_DATA_PATH = BASE_DIR / "data" / "product_catalog.json"
GLOSSARY_DATA_PATH = BASE_DIR / "data" / "glossary.json"
EXPERIMENT_RECORDS_PATH = BASE_DIR / "data" / "experiment_records.json"
EXPERIMENT_RECORD_ATTACHMENTS_DIR = BASE_DIR / "data" / "experiment_record_attachments"
FEATURE_CONFIG_PATH = BASE_DIR / "config" / "features.json"
IMAGE_DIR = BASE_DIR / "images"
PRODUCT_IMAGE_DIR = IMAGE_DIR / "products"
PRODUCT_IMAGE_BY_NUMBER = {
    "362S3001": "onchip_sort.webp",
    "362S3001G": "onchip_sort.webp",
    "362S3001GR": "onchip_sort.webp",
    "262S3001": "onchip_sort.webp",
    "252S3001": "onchip_sort.webp",
    "252S3001G": "onchip_sort.webp",
    "152S3001": "onchip_sort.webp",
    "64682-C": "droplet_generator_s.webp",
    "64002-C": "droplet_generator_s.webp",
    "64602-C": "droplet_generator_s.webp",
    "64681": "droplet_generator_s.webp",
    "64001": "droplet_generator_s.webp",
    "64601": "droplet_generator_s.webp",
    "64682-N": "droplet_generator_s.webp",
    "64002-N": "droplet_generator_s.webp",
    "64602-N": "droplet_generator_s.webp",
    "64000": "droplet_generator_s.webp",
    "60001": "droplet_generator.webp",
    "60002-C": "droplet_generator.webp",
    "60601": "droplet_generator.webp",
    "60602-C": "droplet_generator.webp",
    "60681": "droplet_generator.webp",
    "60682-C": "droplet_generator.webp",
    "362DS001": "droplet_selector.webp",
    "362DS001G": "droplet_selector.webp",
    "362DS001GR": "droplet_selector.webp",
    "262DS001V": "droplet_selector.webp",
    "262DS001R": "droplet_selector.webp",
    "262DS001G": "droplet_selector.webp",
    "88002": "onchip_microdispenser.webp",
    "OM-S-01": "onchip_merge.webp",
    "CF-01": "continuous_flow_adapter.webp",
    "61001": "droplet_generator_temperature_control_unit.webp",
    "1002002": "2d_chip_z101.webp",
    "1002004": "2d_chip_z1001_z1000_w150.webp",
    "1002005": "2d_chip_z1001_z1000_w150.webp",
    "1003002": "2d_chip_800dg.webp",
    "1003003": "2d_chip_1060_1100dg.webp",
    "1003004": "2d_chip_1060_1100dg.webp",
    "1004001": "2d_chip_sd1000.webp",
    "1004002": "2d_chip_sd1000.webp",
    "1007011S": "droplet_series_dispensing_tip_96s.webp",
    "2001014": "onchip_t_buffer.webp",
    "2001015": "sample_buffer_2x_pbs.webp",
    "2003001": "008_fluorosurfactant_5wt_10ml.webp",
    "2003002": "008_fluorosurfactant_0_1wt_100ml.webp",
    "2004001": "onchip_fnap_sort_6_fam.webp",
    "2004002": "onchip_fnap_sort_cy5.webp",
    "2004010": "onchip_mime_stain_green.webp",
    "2004011": "onchip_mime_stain_red.webp",
}
LOGO_PATH = BASE_DIR / "onchip_logo_display.png"
VERSION = "v34-no354"
CONTACT_EMAIL = "tech@on-chip.co.jp"
COMPANY_NAME = "On-chip Biotechnologies"
JOINT_AI_FEATURE_ID = "joint_ai"
JOINT_AI_USAGE_NOTE = "JointAIは施設内AIを介して応答します。所属施設のAI利用ルールに従ってご質問ください。"
GLOSSARY_HOVER_PAGES = {"dg_setup", "sorting_setup", "recovery_setup", "guide", "complete"}

@lru_cache(maxsize=32)
def product_image_data_uri(path_text: str) -> str:
    path = Path(path_text)
    if not path.is_file():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/webp;base64,{encoded}"


st.set_page_config(page_title="On-Chip OpeR", layout="wide")
st.markdown(
    """
<style>
.block-container{max-width:1220px;padding-top:1.8rem;padding-bottom:3rem}
h1{font-size:3rem!important;line-height:1.2!important;letter-spacing:.01em}
.step-title{border-left:8px solid #1677c8;background:#eef7ff;padding:1rem 1.2rem;border-radius:10px;margin:.4rem 0 1.2rem}
.section-title{font-size:1.45rem;font-weight:800;margin-top:1.5rem}
.action-box{border:2px solid #1677c8;background:#f5faff;padding:1rem 1.2rem;border-radius:12px;font-size:1.08rem}
.action-box-row{display:flex;align-items:center;justify-content:space-between;gap:1rem}
.account-setup-link{flex:0 0 auto;color:#0b5fa5;font-size:.95rem;font-weight:800;text-decoration:underline;text-underline-offset:.18em;white-space:nowrap}
.account-setup-link:hover{color:#084a80}
.image-placeholder{border:2px dashed #9aa9b8;background:#f7f9fb;border-radius:14px;padding:2rem 1rem;text-align:center;min-height:230px;display:flex;flex-direction:column;justify-content:center}
.ok-box{border-left:7px solid #1f9d55;background:#effaf3;padding:1rem;border-radius:9px}
.ng-box{border-left:7px solid #d64545;background:#fff1f1;padding:1rem;border-radius:9px}
.warn-box{border-left:7px solid #e0a800;background:#fff9df;padding:1rem;border-radius:9px}
.sop-notice{border:1px solid #e4aab3;border-left:4px solid #b5384c;background:#fff7f8;color:#8f2334;padding:.5rem .72rem;border-radius:8px;margin:.3rem 0 .45rem;font-size:.84rem;line-height:1.45;font-weight:600}
.sop-details{border:1px solid #d7dce2;border-radius:8px;margin:0 0 .65rem;background:#fff;color:#33455a;font-size:.82rem;line-height:1.45}
.sop-details summary{cursor:pointer;padding:.42rem .7rem;font-size:.82rem;line-height:1.35;list-style-position:inside}
.sop-details[open] summary{border-bottom:1px solid #e2e7ec}
.sop-details>div{padding:.48rem .72rem .58rem}
.help-box{border-left:4px solid #8aa4bd;background:#f7f9fb;border-radius:6px;padding:.55rem .8rem;margin:.2rem 0 .7rem 1.8rem;font-size:.88rem;color:#40566b;line-height:1.55}
.home-lead{font-size:1.02rem;margin-bottom:1rem}
.home-card{position:relative;border:1px solid #d8e1eb;border-radius:15px;padding:1.35rem 1.35rem 1.15rem;background:#fff;box-shadow:0 1px 3px rgba(20,45,75,.04);box-sizing:border-box;overflow:hidden}
.home-card.has-badge{padding-bottom:3.35rem}
.home-card.top{height:354px}.home-card.bottom{height:332px}
.home-card-header{margin:0 0 .8rem}
.home-card-header h3{font-size:clamp(1rem,1.9vw,1.18rem);line-height:1.25;margin:0;font-weight:800;white-space:nowrap}
.home-availability-badge{position:absolute;left:1.35rem;bottom:1.05rem;display:inline-flex;align-items:center;justify-content:center;border:1px solid #65a97b;background:#f2fbf5;color:#267144;border-radius:999px;padding:.25rem .58rem;font-size:.76rem;font-weight:800;line-height:1.2;white-space:nowrap}
.home-paid-badge{border-color:#8a63d2;background:#f7f2ff;color:#5a3f9b}
.home-unavailable-badge{border-color:#d86565;background:#fff0f0;color:#a12f2f}
.home-card-unavailable{border-color:#e3aaaa;background:#fff8f8}
.home-card-unavailable .home-card-header h3{color:#8f2f2f}
.home-card-unavailable .home-models{border-color:#e3b3b3;background:#fff2f2;color:#6f3b3b}
.home-card-unavailable .home-models strong{color:#a23939}
.home-card p{font-size:1rem;line-height:1.62;margin:.25rem 0}.home-purpose{margin:.25rem 0!important;font-size:.96rem!important;line-height:1.55!important}.home-status{font-weight:800;margin-top:.35rem}
.home-first-use-note{border-left:4px solid #e0a800;background:#fff9df;color:#5f4b00;border-radius:7px;padding:.55rem .65rem;margin:.75rem 0 0;font-size:.84rem;line-height:1.5;font-weight:700}
.home-feature-list{margin:.2rem 0 .65rem;padding-left:1.25rem;font-size:.98rem;line-height:1.58}.home-feature-list li{margin:.22rem 0}
.home-models{border:1px solid #9fc6e8;background:#f5faff;border-radius:8px;padding:.55rem .7rem;margin:0 0 .85rem;font-size:.88rem;line-height:1.5;color:#27435d}
.home-models strong{color:#0b5fa5}
.joint-ai-files{border:1px solid #c7c2f4;background:linear-gradient(135deg,#f7f8ff 0%,#f5f0ff 100%);border-radius:10px;padding:.62rem .78rem;margin:.45rem 0 .65rem;color:#33405f;font-size:.9rem;line-height:1.55}
.joint-ai-wordmark{display:flex;align-items:center;gap:.05rem;margin:.12rem 0 .62rem;font-size:1.3rem;font-weight:850;line-height:1.2;letter-spacing:.01em}
.joint-ai-wordmark.compact{font-size:1.16rem;margin:0 0 .38rem}
.joint-ai-wordmark .joint-ai-spark{color:#7351e7;margin-right:.18rem;font-size:.9em}
.joint-ai-wordmark .joint-ai-joint{color:#102a56}
.joint-ai-wordmark .joint-ai-ai{background:linear-gradient(90deg,#754fe8 0%,#2f73df 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
.joint-ai-overview{border:1px solid #d7d2f6;border-left:4px solid #7351e7;background:linear-gradient(135deg,#fbfcff 0%,#f7f4ff 100%);border-radius:10px;padding:.82rem .9rem;margin:.15rem 0 .72rem;color:#33405f;font-size:.9rem;line-height:1.72}
.joint-ai-overview b{display:block;color:#173d66;font-size:.98rem;margin-bottom:.35rem}
.joint-ai-overview strong{color:#173d66}
.joint-ai-sidebar-guide{color:#52677b;font-size:.82rem;line-height:1.5;margin:.15rem 0 .35rem}
.joint-ai-sidebar-heading .joint-ai-wordmark{margin:0!important;min-height:2.05rem;padding:.28rem .5rem;box-sizing:border-box}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.joint-ai-sidebar-heading){align-items:center!important;gap:.2rem!important;margin:.08rem 0 -.16rem!important}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.joint-ai-sidebar-heading)>div[data-testid="stColumn"]:first-child{flex:1 1 auto!important;width:auto!important;min-width:0!important}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.joint-ai-sidebar-heading)>div[data-testid="stColumn"]:last-child{flex:0 0 2.2rem!important;width:2.2rem!important;min-width:2.2rem!important}
section[data-testid="stSidebar"] .st-key-joint_ai_sidebar_toggle button{height:2.05rem!important;min-height:2.05rem!important;padding:0!important;border:1px solid #d8e1eb!important;border-radius:8px!important;background:#fff!important;color:#52677b!important;box-shadow:none!important;font-size:.92rem!important}
section[data-testid="stSidebar"] .st-key-joint_ai_sidebar_toggle button:hover{border-color:#8874ea!important;color:#5a3f9b!important;background:#f8f6ff!important}
.joint-ai-usage-note{font-size:.76rem;color:#68798a;line-height:1.45;padding:.05rem 0}
div[data-testid="stHorizontalBlock"]:has(.joint-ai-usage-note){align-items:center!important;gap:.72rem!important;margin:.5rem 0 .6rem}
.st-key-home_joint_ai_toggle{margin-top:.3rem}
[class*="st-key-joint_ai_toggle_"]{margin:0!important}
[class*="st-key-joint_ai_toggle_"] button{width:10.5rem!important;min-width:10.5rem!important}
.st-key-home_joint_ai_toggle button,[class*="st-key-joint_ai_toggle_"] button{background:linear-gradient(135deg,#ffffff 0%,#f7f4ff 100%)!important;border:1px solid #8874ea!important;color:transparent!important;border-radius:999px!important;box-shadow:0 8px 22px rgba(66,72,190,.20)!important;font-weight:850!important;letter-spacing:.02em!important;transition:transform .15s ease,box-shadow .15s ease,filter .15s ease!important}
.st-key-home_joint_ai_toggle button p,[class*="st-key-joint_ai_toggle_"] button p{background:linear-gradient(90deg,#7351e7 0%,#7351e7 14%,#102a56 19%,#102a56 69%,#754fe8 79%,#2f73df 100%);-webkit-background-clip:text;background-clip:text;color:transparent!important;font-weight:850!important}
.st-key-home_joint_ai_toggle button:hover,[class*="st-key-joint_ai_toggle_"] button:hover{transform:translateY(-1px);box-shadow:0 10px 26px rgba(66,72,190,.30)!important;filter:brightness(1.02)}
section[data-testid="stSidebar"] .st-key-joint_ai_file_upload [data-testid="stFileUploaderDropzone"]{border:1.5px dashed #7167d9;background:linear-gradient(135deg,#fbfcff 0%,#f6f2ff 100%);border-radius:14px}
section[data-testid="stSidebar"] .st-key-joint_ai_file_upload [data-testid="stFileUploaderDropzoneInstructions"]{color:#33405f}
.st-key-joint_ai_master_file_upload [data-testid="stFileUploaderDropzone"]{border:1.5px dashed #7167d9;background:linear-gradient(135deg,#fbfcff 0%,#f6f2ff 100%);border-radius:14px}
.st-key-joint_ai_master_file_upload [data-testid="stFileUploaderDropzoneInstructions"]{color:#33405f}
.layout-mode-switch-spacer{height:.72rem}
div[data-testid="stHorizontalBlock"]:has(.layout-mode-divider){align-items:center!important;gap:0!important}
.st-key-layout_mode_beginner,.st-key-layout_mode_master{display:flex!important;align-items:center!important;justify-content:center!important}
.st-key-layout_mode_beginner button,.st-key-layout_mode_master button{min-height:0!important;height:auto!important;width:auto!important;padding:0!important;border:none!important;background:transparent!important;box-shadow:none!important;color:#52677b!important;font-size:.82rem!important;font-weight:500!important;white-space:nowrap!important}
.st-key-layout_mode_beginner button p,.st-key-layout_mode_master button p{color:inherit!important;font-size:inherit!important;font-weight:inherit!important;margin:0!important}
.st-key-layout_mode_beginner button[kind="primary"],.st-key-layout_mode_master button[kind="primary"]{color:#1677c8!important;font-weight:750!important}
.st-key-layout_mode_beginner button:hover,.st-key-layout_mode_master button:hover{color:#1677c8!important;text-decoration:underline!important;background:transparent!important;border:none!important;box-shadow:none!important}
.layout-mode-divider{text-align:center;color:#8a98a6;font-size:.82rem;line-height:1.2;white-space:nowrap}
.selection-choice-image{height:clamp(165px,18vw,225px);display:flex;align-items:center;justify-content:center;overflow:hidden;border-radius:11px;background:linear-gradient(180deg,#fff 0%,#f8fafc 100%);border:1px solid #e0e7ee;padding:.55rem}
.selection-choice-image.chip{height:clamp(125px,14vw,175px)}
.selection-choice-image img{display:block;width:100%;height:100%;object-fit:contain;border-radius:8px}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.selection-choice-image){border:1px solid #c9d9e8!important;border-radius:14px!important;background:#fff!important;margin:.3rem 0 .8rem!important;box-shadow:0 1px 4px rgba(20,45,75,.05)!important}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.selection-choice-image)>div{padding:.72rem!important}
.fluor-spectrum-figure{width:100%;margin:.45rem 0 .9rem}
.fluor-spectrum-figure svg{display:block;width:100%;height:auto}
@media (max-width:700px){.selection-choice-image{height:190px}.selection-choice-image.chip{height:150px}.joint-ai-usage-note{padding:0 0 .25rem}}
div[data-testid="stButton"]>button{border-radius:8px;min-height:2.65rem;font-weight:700}
div[data-testid="stRadio"] > div{gap:.55rem!important}
div[data-testid="stRadio"] label{border:none!important;background:transparent!important;border-radius:0!important;padding:.15rem 0!important;display:flex!important;align-items:center!important}
div[data-testid="stRadio"] label:hover{border:none!important;background:transparent!important}
.branch-choice-note{border-left:4px solid #1677c8;background:#f5faff;padding:.55rem .8rem;border-radius:8px;margin:.35rem 0 .55rem;color:#334b63;font-weight:700}

div[data-testid="stButton"]>button[kind="primary"]{background-color:#1677c8!important;border-color:#1677c8!important;color:#fff!important}
div[data-testid="stButton"]>button[kind="primary"]:disabled{background-color:#1677c8!important;border-color:#1677c8!important;color:#fff!important;opacity:1!important}
.st-key-home_start_beginner button,.st-key-home_start_sorting button,.st-key-home_start_recovery button,.st-key-home_experiment_pending button,.st-key-home_open_experiment button,.st-key-home_open_results button,.st-key-home_open_trouble button{background-color:#1677c8!important;border-color:#1677c8!important;color:#fff!important;opacity:1!important}
.st-key-home_start_beginner button:disabled,.st-key-home_experiment_pending button:disabled{background-color:#1677c8!important;border-color:#1677c8!important;color:#fff!important;opacity:1!important}
.home-disabled{border:1px solid #d6dce3;border-radius:8px;text-align:center;padding:.58rem;color:#a5adb7;margin-top:.55rem}
.dg-choice-card{border:1px solid #c9d9e8;border-radius:14px;background:#fff;padding:1rem 1.1rem;margin:.35rem 0 .8rem;box-shadow:0 1px 3px rgba(20,45,75,.04)}
.dg-choice-card strong{font-size:1.05rem}.dg-choice-note{font-size:.9rem;color:#52677b;line-height:1.55;margin-top:.35rem}
.dg-summary{border:2px solid #70aee1;background:#f5faff;border-radius:14px;padding:1rem 1.15rem;margin:1rem 0}
.recovery-summary-selected{font-weight:800;color:#0b5fa5}
.recovery-choice-marker{display:block;width:0;height:0;overflow:hidden}
.recovery-choice-title{font-size:1.05rem;font-weight:800;color:#173d66;margin:.15rem 0 .35rem}
.recovery-choice-note{font-size:.9rem;color:#52677b;line-height:1.58;min-height:3.1rem;margin:.1rem 0 .85rem}
.recovery-choice-double{display:grid;grid-template-columns:1fr 1fr;gap:.75rem;margin-bottom:.2rem}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.recovery-choice-marker){border:1px solid #c9d9e8!important;border-radius:14px!important;background:#fff!important;margin:.3rem 0 .8rem!important;box-shadow:0 1px 4px rgba(20,45,75,.05)!important;height:100%}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.recovery-choice-marker)>div{padding:.78rem!important;height:100%}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.recovery-choice-marker) div[data-testid="stButton"]{margin-top:auto!important}

section[data-testid="stSidebar"]{background:#f3f6fa}
section[data-testid="stSidebar"] .block-container{padding-top:1.6rem}
.sidebar-step{font-size:.92rem;padding:.35rem 0;border-bottom:1px solid #dfe6ee}
.sidebar-current{font-weight:800;color:#0068c9}
section[data-testid="stSidebar"] [class*="st-key-sidebar_step_"] button{width:100%;display:flex!important;border:none!important;border-bottom:1px solid #dfe6ee!important;border-radius:0!important;background:transparent!important;padding:.42rem .35rem .42rem .65rem!important;min-height:0!important;font-size:.92rem!important;font-weight:400!important;justify-content:flex-start!important;text-align:left!important;box-shadow:none!important;color:#23364a!important}
section[data-testid="stSidebar"] [class*="st-key-sidebar_step_"] button>div,section[data-testid="stSidebar"] [class*="st-key-sidebar_step_"] button [data-testid="stMarkdownContainer"]{width:100%!important;display:block!important;text-align:left!important}
section[data-testid="stSidebar"] [class*="st-key-sidebar_step_"] button p{text-align:left!important;white-space:normal!important;margin:0!important}
section[data-testid="stSidebar"] [class*="st-key-sidebar_step_"] button:hover{background:#eaf1f8!important}
section[data-testid="stSidebar"] [class*="st-key-sidebar_step_current_"] button{font-weight:800!important;color:#0068c9!important}
[class*="st-key-skip_step_"] button{margin-top:.4rem;min-height:5.55rem!important;background-color:#1677c8!important;border-color:#1677c8!important;color:#fff!important}
div[data-testid="stRadio"] > div{gap:.55rem!important}
div[data-testid="stRadio"] label{border:none!important;background:transparent!important;border-radius:0!important;padding:.15rem 0!important;display:flex!important;align-items:center!important}
div[data-testid="stRadio"] label:hover{border:none!important;background:transparent!important}
.branch-choice-note{border-left:4px solid #1677c8;background:#f5faff;padding:.55rem .8rem;border-radius:8px;margin:.35rem 0 .55rem;color:#334b63;font-weight:700}
div[data-testid="stCheckbox"] label[data-baseweb="checkbox"]{gap:.42rem!important;align-items:flex-start!important;padding:0!important}
div[data-testid="stRadio"] > div{gap:.55rem!important}
div[data-testid="stRadio"] label{border:none!important;background:transparent!important;border-radius:0!important;padding:.15rem 0!important;display:flex!important;align-items:center!important}
div[data-testid="stRadio"] label:hover{border:none!important;background:transparent!important}
.branch-choice-note{border-left:4px solid #1677c8;background:#f5faff;padding:.55rem .8rem;border-radius:8px;margin:.35rem 0 .55rem;color:#334b63;font-weight:700}
div[data-testid="stCheckbox"] label[data-baseweb="checkbox"]>span:first-child{width:1.2rem!important;height:1.2rem!important;min-width:1.2rem!important;margin-top:.08rem!important}
div[data-testid="stRadio"] > div{gap:.55rem!important}
div[data-testid="stRadio"] label{border:none!important;background:transparent!important;border-radius:0!important;padding:.15rem 0!important;display:flex!important;align-items:center!important}
div[data-testid="stRadio"] label:hover{border:none!important;background:transparent!important}
.branch-choice-note{border-left:4px solid #1677c8;background:#f5faff;padding:.55rem .8rem;border-radius:8px;margin:.35rem 0 .55rem;color:#334b63;font-weight:700}
div[data-testid="stCheckbox"] label[data-baseweb="checkbox"]>span:last-child{margin:0!important;padding:0!important;font-size:.875rem!important;line-height:1.5!important}
div[data-testid="stCheckbox"] input[type="checkbox"]+div{width:1.2rem!important;height:1.2rem!important}
div[data-testid="stCheckbox"] input[type="checkbox"]:not(:checked)+div{border:2px solid #6f7f90!important}
div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stCheckbox"]){width:94%;margin:.2rem auto .8rem!important;border:2px solid #70aee1!important;background:#f5faff!important;border-radius:14px!important;box-shadow:0 2px 8px rgba(22,119,200,.08)!important}
div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stCheckbox"])>div{padding:.85rem 1.1rem .5rem!important}
div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stCheckbox"]) div[data-testid="stCheckbox"]{margin:.1rem 0 .25rem}
section[data-testid="stSidebar"] [class*="st-key-sidebar_menu_"]{margin-bottom:-.42rem!important}
section[data-testid="stSidebar"] [class*="st-key-sidebar_menu_"] button{min-height:2.05rem!important;padding:.28rem .5rem!important;font-size:.86rem!important;font-weight:600!important}
.sidebar-footer{margin-top:2rem;padding-top:.9rem;border-top:1px solid #d8e1eb;color:#7b8794;font-size:.72rem;line-height:1.55}
.sidebar-footer .product-name{font-weight:700;color:#657382;margin-bottom:.2rem}
@media (max-width:900px){.block-container{padding-left:1rem;padding-right:1rem}.home-card.top,.home-card.bottom{height:auto;min-height:auto}.home-card-header h3{white-space:normal}}
.product-hero{border:2px solid #1677c8;background:linear-gradient(135deg,#eef7ff,#fff);border-radius:16px;padding:1.1rem 1.25rem;margin:.35rem 0 1rem;line-height:1.65}
.product-card{border:1px solid #d8e1eb;background:#fff;border-radius:14px;padding:1rem 1.05rem;margin:.35rem 0 .8rem;box-shadow:0 1px 3px rgba(20,45,75,.04);min-height:190px}
.product-card-title{font-size:1.08rem;font-weight:850;color:#173d66;line-height:1.4;margin-bottom:.25rem}
.product-card-number{font-size:.86rem;color:#647588;margin-bottom:.65rem}
.product-card-category{display:inline-block;border:1px solid #9fc6e8;background:#f5faff;color:#0b5fa5;border-radius:999px;padding:.18rem .5rem;font-size:.74rem;font-weight:750;margin-bottom:.65rem}
.product-card-body.has-image{display:grid;grid-template-columns:minmax(0,1fr) minmax(150px,42%);gap:.85rem;align-items:stretch}
.product-card-attributes{min-width:0}
.product-card-image-wrap{display:flex;align-items:center;justify-content:center;min-height:180px;border-left:1px solid #e6ebf0;padding:.25rem 0 .25rem .85rem}
.product-card-image{display:block;width:100%;max-width:230px;max-height:220px;object-fit:contain;border-radius:8px}
.product-attribute{border-top:1px solid #e6ebf0;padding:.42rem 0;font-size:.88rem;line-height:1.5}
.product-attribute b{color:#334d68}
.product-note{border-left:5px solid #e0a800;background:#fff9df;border-radius:8px;padding:.65rem .8rem;margin:.45rem 0;line-height:1.55}
.product-hover-ref{position:relative;display:inline-block;color:#075f9e;font-weight:800;border-bottom:1px dotted #1677c8;cursor:help;outline:none}
.product-hover-ref::after{content:"";position:absolute;left:0;top:100%;width:100%;height:.55rem}
.product-hover-card{display:block;position:absolute;z-index:10000;left:0;top:calc(100% + .5rem);width:min(500px,calc(100vw - 5rem));box-sizing:border-box;border:1px solid #c7d9e9;background:#fff;border-radius:14px;padding:.9rem 1rem;box-shadow:0 12px 30px rgba(20,45,75,.22);color:#23364a;font-size:.88rem;font-weight:400;line-height:1.5;text-align:left;white-space:normal;opacity:0;visibility:hidden;transform:translateY(-4px);transition:opacity .12s ease,transform .12s ease,visibility .12s;pointer-events:none}
.product-hover-ref:hover .product-hover-card{opacity:1;visibility:visible;transform:translateY(0);pointer-events:none}
.product-hover-card-category{display:inline-block;border:1px solid #9fc6e8;background:#f5faff;color:#0b5fa5;border-radius:999px;padding:.14rem .46rem;font-size:.72rem;font-weight:750;margin-bottom:.5rem}
.product-hover-card-title{display:block;font-size:1.05rem;font-weight:850;color:#173d66;line-height:1.4;margin-bottom:.16rem}
.product-hover-card-number{display:block;font-size:.82rem;color:#647588;margin-bottom:.5rem}
.product-hover-card-body.has-image{display:grid;grid-template-columns:minmax(0,1fr) minmax(120px,36%);gap:.75rem;align-items:stretch}
.product-hover-card-attributes{display:block;min-width:0}
.product-hover-card-image-wrap{display:flex;align-items:center;justify-content:center;min-height:128px;border-left:1px solid #e6ebf0;padding:.2rem 0 .2rem .75rem}
.product-hover-card-image{display:block;width:100%;max-width:170px;max-height:160px;object-fit:contain;border-radius:7px}
.product-hover-card-attribute{display:block;border-top:1px solid #e6ebf0;padding:.36rem 0;line-height:1.5}
.product-hover-card-attribute b{color:#334d68}
.prep-check-row{padding:.2rem 0 .28rem;font-size:.875rem!important;line-height:1.55}
div[data-testid="stHorizontalBlock"]:has(.prep-check-row){gap:.42rem!important;align-items:flex-start!important}
div[data-testid="stHorizontalBlock"]:has(.prep-check-row)>div[data-testid="stColumn"]:first-child{flex:0 0 1.2rem!important;width:1.2rem!important;min-width:1.2rem!important}
div[data-testid="stHorizontalBlock"]:has(.prep-check-row)>div[data-testid="stColumn"]:nth-child(2){flex:1 1 auto!important;width:auto!important;min-width:0!important}
div[data-testid="stHorizontalBlock"]:has(.prep-check-row) div[data-testid="stCheckbox"]{margin:.02rem 0 0!important}
div[data-testid="stHorizontalBlock"]:has(.prep-check-row) div[data-testid="stCheckbox"] label{padding:0!important}
.fluor-system-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.65rem;margin:.65rem 0 .9rem}
.fluor-system-grid>div{border:1px solid #c9d9e8;border-radius:10px;background:#f9fbfd;padding:.75rem .85rem;line-height:1.55}
.fluor-system-grid strong{display:block;color:#0b5fa5;margin-bottom:.18rem}
.fluor-table-wrap{width:100%;overflow:visible;margin:.45rem 0 .7rem}
.fluor-table{width:100%;min-width:920px;border-collapse:separate;border-spacing:0;font-size:.86rem;line-height:1.45}
.fluor-table th,.fluor-table td{border-right:1px solid #dce5ed;border-bottom:1px solid #dce5ed;padding:.62rem .66rem;vertical-align:top;text-align:left;background:#fff}
.fluor-table th{background:#eef7ff;color:#173d66;font-weight:850;text-align:center}
.fluor-table th:first-child,.fluor-table td:first-child{border-left:1px solid #dce5ed;font-weight:850;white-space:nowrap}
.fluor-table thead th{border-top:1px solid #dce5ed}
.fluor-table thead th:first-child{border-top-left-radius:9px}
.fluor-table thead th:last-child{border-top-right-radius:9px}
.fluor-empty{color:#a0acb8;text-align:center!important}
@media (max-width:900px){.product-card{min-height:auto}.product-card-body.has-image{grid-template-columns:1fr}.product-card-image-wrap{min-height:150px;border-left:0;border-top:1px solid #e6ebf0;padding:.8rem 0 0}.product-hover-card{position:fixed;left:1rem;right:1rem;top:auto;bottom:1rem;width:auto;max-height:72vh;overflow:auto}.product-hover-card-body.has-image{grid-template-columns:minmax(0,1fr) minmax(110px,34%)}.product-hover-card-image-wrap{min-height:112px}.fluor-system-grid{grid-template-columns:1fr}.fluor-table-wrap{overflow-x:auto}}

.results-hero{border:2px solid #1677c8;background:linear-gradient(135deg,#eef7ff,#ffffff);border-radius:16px;padding:1.25rem 1.4rem;margin:.35rem 0 1rem}
.results-hero-title{font-size:1.35rem;font-weight:850;color:#0b5fa5;margin-bottom:.35rem}
.results-roadmap{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.65rem;margin:.8rem 0 1.25rem}
.results-roadmap-item{border:1px solid #c9d9e8;background:#fff;border-radius:10px;padding:.65rem .75rem;font-size:.92rem;line-height:1.45}
.results-roadmap-item b{color:#0b5fa5}
[class*="st-key-results_open_"] button{min-height:4.55rem!important;justify-content:flex-start!important;text-align:left!important;background:#fff!important;border:1px solid #c9d9e8!important;color:#23364a!important;padding:.65rem .8rem!important}
[class*="st-key-results_open_"] button:hover{border-color:#1677c8!important;background:#f5faff!important}
[class*="st-key-results_open_"] button p{white-space:pre-line!important;text-align:left!important;line-height:1.42!important;margin:0!important}
.results-page-context{font-size:.92rem;color:#647588;margin:.15rem 0 .8rem}
.result-step-title{border-left:8px solid #1677c8;background:#eef7ff;border-radius:10px;padding:.82rem 1rem;margin:1.8rem 0 .85rem;font-size:1.32rem;font-weight:850}
.result-card{border:1px solid #d8e1eb;background:#fff;border-radius:12px;padding:1rem 1.1rem;margin:.45rem 0 .9rem;box-shadow:0 1px 3px rgba(20,45,75,.04);line-height:1.7}
.result-key{border-left:6px solid #1f9d55;background:#effaf3;border-radius:9px;padding:.8rem 1rem;margin:.55rem 0 .9rem;line-height:1.65}
.result-general{border-left:6px solid #8a63d2;background:#f7f2ff;border-radius:9px;padding:.8rem 1rem;margin:.55rem 0 .9rem;line-height:1.65}
.result-caution{border-left:6px solid #e0a800;background:#fff9df;border-radius:9px;padding:.8rem 1rem;margin:.55rem 0 .9rem;line-height:1.65}
.result-source{font-size:.82rem;color:#647588;line-height:1.5;margin-top:.15rem}
.result-explainer-marker{display:none}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.result-explainer-marker){border:1px solid #c9d9e8!important;border-radius:14px!important;background:#fff!important;margin:.7rem 0 1rem!important;box-shadow:0 1px 4px rgba(20,45,75,.05)!important}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.result-explainer-marker)>div{padding:1rem 1.1rem!important}
.result-explainer-copy{height:100%;display:flex;flex-direction:column;justify-content:center;line-height:1.72;padding:.15rem .1rem}
.result-explainer-copy h3{font-size:1.22rem;color:#0b5fa5;margin:0 0 .55rem;font-weight:850;line-height:1.35}
.result-explainer-copy p{margin:0;font-size:1rem;line-height:1.72}
.result-explainer-copy .result-explainer-note{margin-top:.65rem;padding:.58rem .7rem;border-left:4px solid #1f9d55;background:#effaf3;border-radius:6px;font-size:.9rem;line-height:1.55}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.result-explainer-marker) [data-testid="stImage"]{margin:.05rem 0 0}

.result-compare{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.7rem;margin:.75rem 0 1rem}
.result-compare>div{border:1px solid #c9d9e8;border-radius:10px;background:#f9fbfd;padding:.85rem .9rem;line-height:1.62}
.result-compare strong{display:block;color:#0b5fa5;margin-bottom:.25rem}
.glossary-hero{border:2px solid #1677c8;background:linear-gradient(135deg,#eef7ff,#fff);border-radius:16px;padding:1.1rem 1.25rem;margin:.35rem 0 1rem;line-height:1.7}
.glossary-category{font-size:1.18rem;font-weight:850;color:#0b5fa5;margin:1.35rem 0 .45rem;padding-left:.7rem;border-left:6px solid #1677c8}
.glossary-table{border:1px solid #c9d9e8;border-radius:12px;overflow:hidden;background:#fff;margin-bottom:.9rem}
.glossary-row{display:grid;grid-template-columns:minmax(180px,24%) 1fr;border-bottom:1px solid #dce5ed;line-height:1.65}
.glossary-row:last-child{border-bottom:none}
.glossary-term{background:#f6f9fc;padding:.72rem .85rem;font-weight:850;color:#173d66;border-right:1px solid #dce5ed}
.glossary-aliases{display:block;font-size:.76rem;font-weight:500;color:#647588;margin-top:.18rem;line-height:1.45}
.glossary-description{padding:.72rem .9rem;color:#23364a}
.glossary-empty{border:1px solid #d8e1eb;background:#f7f9fb;border-radius:12px;padding:1rem 1.1rem;color:#52677b}
@media (max-width:700px){.glossary-row{grid-template-columns:1fr}.glossary-term{border-right:none;border-bottom:1px solid #e6ebf0}.glossary-description{padding:.7rem .85rem}}
.results-ai{border:2px dashed #8aa4bd;background:#f7f9fb;border-radius:14px;padding:1.15rem 1.25rem;margin:1rem 0;line-height:1.7}
@media (max-width:900px){.results-roadmap,.result-compare{grid-template-columns:1fr}.result-step-title{font-size:1.15rem}.result-explainer-copy{padding:0 0 .35rem}}
</style>
""",
    unsafe_allow_html=True,
)


def load_data() -> dict:
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        st.error(f"手順データを読み込めませんでした: {exc}")
        st.stop()

    required = {"workflows", "contact", "sop_notice", "troubleshooting"}
    missing = sorted(required - set(data))
    if missing:
        st.error(f"manual_steps.json に必要な項目がありません: {', '.join(missing)}")
        st.stop()
    return data


DATA = load_data()

try:
    PRODUCT_CATALOG = load_product_catalog(PRODUCT_DATA_PATH)
    PRODUCT_CATALOG_ERROR = ""
    PRODUCT_NAME_INDEX = build_product_name_index(PRODUCT_CATALOG)
except (OSError, ValueError, json.JSONDecodeError) as exc:
    PRODUCT_CATALOG = {}
    PRODUCT_NAME_INDEX = {}
    PRODUCT_CATALOG_ERROR = str(exc)

try:
    GLOSSARY = json.loads(GLOSSARY_DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(GLOSSARY, dict) or not isinstance(GLOSSARY.get("entries"), list):
        raise ValueError("用語集データの形式が正しくありません。")
    GLOSSARY_ERROR = ""
except (OSError, ValueError, json.JSONDecodeError) as exc:
    GLOSSARY = {"categories": [], "entries": []}
    GLOSSARY_ERROR = str(exc)

JOINT_AI_CONNECTOR = AIConnector.from_feature_config(
    FEATURE_CONFIG_PATH,
    feature_id=JOINT_AI_FEATURE_ID,
)


def build_glossary_hover_entries(glossary: dict) -> list[dict[str, str]]:
    """Build a de-duplicated hover index; official terms take priority over aliases."""
    entries = glossary.get("entries", []) if isinstance(glossary, dict) else []
    indexed: dict[str, dict[str, str]] = {}

    for item in entries:
        if not isinstance(item, dict):
            continue
        term = str(item.get("term", "")).strip()
        description = str(item.get("description", "")).strip()
        if term and description:
            indexed.setdefault(
                term.casefold(),
                {"match": term, "description": description},
            )

    for item in entries:
        if not isinstance(item, dict):
            continue
        description = str(item.get("description", "")).strip()
        if not description:
            continue
        for alias in item.get("aliases", []):
            alias_text = str(alias).strip()
            if alias_text:
                indexed.setdefault(
                    alias_text.casefold(),
                    {"match": alias_text, "description": description},
                )

    return sorted(
        indexed.values(),
        key=lambda item: (-len(item["match"]), item["match"].casefold()),
    )


GLOSSARY_HOVER_ENTRIES = build_glossary_hover_entries(GLOSSARY)


def init_state() -> None:
    defaults = {
        "page": "home",
        "workflow_key": "analysis",
        "step_index": 0,
        "completed": {},
        "observations": [],
        "step_branches": {},
        "notes": {},
        "scroll_to_top": False,
        "dg_device": "",
        "dg_chip": "",
        "dg_product": "",
        "sorting_device": "",
        "sorting_purpose": "",
        "recovery_method": "",
        "result_step": "",
        "account_setup_device": "",
        "active_experiment_record_id": "",
        "experiment_record_draft": None,
        "experiment_record_return_page": "home",
        "joint_ai_sidebar_expanded": False,
        "layout_mode": "beginner",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def request_scroll_to_top() -> None:
    st.session_state.scroll_to_top = True


def apply_scroll_to_top() -> None:
    if st.session_state.pop("scroll_to_top", False):
        components.html(
            """<script>
            const scrollToTop = () => {
                const parentDocument = window.parent.document;
                const appContainer = parentDocument.querySelector(
                    '[data-testid="stAppViewContainer"]'
                );
                const mainContainer = parentDocument.querySelector(
                    '[data-testid="stMain"]'
                );

                if (appContainer) appContainer.scrollTo(0, 0);
                if (mainContainer) mainContainer.scrollTo(0, 0);
                parentDocument.documentElement.scrollTo(0, 0);
                parentDocument.body.scrollTo(0, 0);
                window.parent.scrollTo(0, 0);
            };

            requestAnimationFrame(() => {
                scrollToTop();
                setTimeout(scrollToTop, 100);
                setTimeout(scrollToTop, 300);
            });
            </script>""",
            height=0,
            width=0,
        )


def apply_glossary_hover(*, enabled: bool) -> None:
    """Install a non-interactive glossary tooltip over rendered main-page text."""
    payload = json.dumps(
        GLOSSARY_HOVER_ENTRIES if enabled and not GLOSSARY_ERROR else [],
        ensure_ascii=True,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    components.html(
        f"""<script>
(() => {{
    const hostWindow = window.parent;
    const doc = hostWindow.document;
    const previous = hostWindow.__onchipGlossaryHoverController;
    if (previous && typeof previous.destroy === "function") previous.destroy();

    const entries = {payload};
    if (!entries.length) {{
        delete hostWindow.__onchipGlossaryHoverController;
        return;
    }}

    const tooltip = doc.createElement("div");
    tooltip.id = "onchip-glossary-hover-tooltip";
    tooltip.setAttribute("role", "tooltip");
    Object.assign(tooltip.style, {{
        position: "fixed",
        zIndex: "2147483646",
        display: "none",
        maxWidth: "min(290px, calc(100vw - 24px))",
        boxSizing: "border-box",
        padding: "7px 9px",
        border: "1px solid rgba(124, 145, 166, .55)",
        borderRadius: "7px",
        background: "rgba(255, 255, 255, .97)",
        boxShadow: "0 4px 14px rgba(30, 55, 80, .14)",
        color: "#33475b",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        fontSize: "12px",
        fontWeight: "400",
        lineHeight: "1.5",
        letterSpacing: "normal",
        textAlign: "left",
        whiteSpace: "normal",
        overflowWrap: "anywhere",
        pointerEvents: "none",
        userSelect: "none",
        opacity: "0",
        transition: "opacity .10s ease"
    }});
    doc.body.appendChild(tooltip);

    const prepared = entries.map((entry) => ({{
        ...entry,
        needle: entry.match.toLocaleLowerCase("ja-JP")
    }}));
    const excludedSelector = [
        "script", "style", "textarea", "input", "select", "option",
        "[contenteditable='true']", ".product-hover-ref", ".product-hover-card",
        "#onchip-glossary-hover-tooltip"
    ].join(",");

    let frame = 0;
    let showTimer = 0;
    let visibleKey = "";
    let lastEvent = null;

    const hide = () => {{
        if (showTimer) hostWindow.clearTimeout(showTimer);
        showTimer = 0;
        visibleKey = "";
        tooltip.style.opacity = "0";
        tooltip.style.display = "none";
    }};

    const positionTooltip = (x, y) => {{
        tooltip.style.left = `${{x + 12}}px`;
        tooltip.style.top = `${{y + 14}}px`;
        const rect = tooltip.getBoundingClientRect();
        let left = x + 12;
        let top = y + 14;
        if (left + rect.width > hostWindow.innerWidth - 8) {{
            left = Math.max(8, x - rect.width - 12);
        }}
        if (top + rect.height > hostWindow.innerHeight - 8) {{
            top = Math.max(8, y - rect.height - 12);
        }}
        tooltip.style.left = `${{left}}px`;
        tooltip.style.top = `${{top}}px`;
    }};

    const pointInsideRange = (range, x, y) => {{
        for (const rect of range.getClientRects()) {{
            if (
                x >= rect.left - 1 && x <= rect.right + 1 &&
                y >= rect.top - 1 && y <= rect.bottom + 1
            ) return true;
        }}
        return false;
    }};

    const hasLatinLetterBeside = (text, index) => {{
        if (index < 0 || index >= text.length) return false;
        return /[A-Za-z]/.test(text[index]);
    }};

    const findMatch = (node, offset, x, y) => {{
        if (!node || node.nodeType !== Node.TEXT_NODE || !node.parentElement) return null;
        const parent = node.parentElement;
        const main = doc.querySelector('[data-testid="stMain"]');
        if (!main || !main.contains(parent) || parent.closest(excludedSelector)) return null;

        const source = node.nodeValue || "";
        if (!source.trim()) return null;
        const lowered = source.toLocaleLowerCase("ja-JP");

        for (const entry of prepared) {{
            let start = lowered.indexOf(entry.needle);
            while (start !== -1) {{
                const end = start + entry.needle.length;
                const isAtWord = offset >= start && offset <= end;
                const startsLatin = /^[A-Za-z]/.test(entry.match);
                const endsLatin = /[A-Za-z]$/.test(entry.match);
                const leftClear = !startsLatin || !hasLatinLetterBeside(source, start - 1);
                const rightClear = !endsLatin || !hasLatinLetterBeside(source, end);
                if (isAtWord && leftClear && rightClear) {{
                    const range = doc.createRange();
                    range.setStart(node, start);
                    range.setEnd(node, end);
                    if (pointInsideRange(range, x, y)) {{
                        return {{ entry, start, end }};
                    }}
                }}
                start = lowered.indexOf(entry.needle, start + 1);
            }}
        }}
        return null;
    }};

    const textPositionFromPoint = (x, y) => {{
        if (typeof doc.caretRangeFromPoint === "function") {{
            const range = doc.caretRangeFromPoint(x, y);
            if (range) return {{ node: range.startContainer, offset: range.startOffset }};
        }}
        if (typeof doc.caretPositionFromPoint === "function") {{
            const pos = doc.caretPositionFromPoint(x, y);
            if (pos) return {{ node: pos.offsetNode, offset: pos.offset }};
        }}
        return null;
    }};

    const evaluate = () => {{
        frame = 0;
        const event = lastEvent;
        if (!event || event.pointerType === "touch") {{
            hide();
            return;
        }}
        const pos = textPositionFromPoint(event.clientX, event.clientY);
        const match = pos && findMatch(pos.node, pos.offset, event.clientX, event.clientY);
        if (!match) {{
            hide();
            return;
        }}

        const key = `${{match.entry.match}}\u0000${{match.entry.description}}`;
        if (visibleKey === key && tooltip.style.display === "block") {{
            positionTooltip(event.clientX, event.clientY);
            return;
        }}

        if (showTimer) hostWindow.clearTimeout(showTimer);
        visibleKey = key;
        tooltip.textContent = match.entry.description;
        showTimer = hostWindow.setTimeout(() => {{
            tooltip.style.display = "block";
            positionTooltip(event.clientX, event.clientY);
            hostWindow.requestAnimationFrame(() => {{ tooltip.style.opacity = "1"; }});
            showTimer = 0;
        }}, 170);
    }};

    const onPointerMove = (event) => {{
        lastEvent = event;
        if (!frame) frame = hostWindow.requestAnimationFrame(evaluate);
    }};
    const onHide = () => hide();

    doc.addEventListener("pointermove", onPointerMove, true);
    doc.addEventListener("pointerdown", onHide, true);
    doc.addEventListener("scroll", onHide, true);
    hostWindow.addEventListener("resize", onHide);
    doc.addEventListener("mouseleave", onHide);

    hostWindow.__onchipGlossaryHoverController = {{
        destroy() {{
            if (frame) hostWindow.cancelAnimationFrame(frame);
            if (showTimer) hostWindow.clearTimeout(showTimer);
            doc.removeEventListener("pointermove", onPointerMove, true);
            doc.removeEventListener("pointerdown", onHide, true);
            doc.removeEventListener("scroll", onHide, true);
            hostWindow.removeEventListener("resize", onHide);
            doc.removeEventListener("mouseleave", onHide);
            tooltip.remove();
        }}
    }};
}})();
</script>""",
        height=0,
        width=0,
    )


def is_transient_widget_key(key: str) -> bool:
    return (
        key.startswith("branch_")
        or key.startswith("note_")
        or "_op_" in key
        or "_check_" in key
    )


def clear_step_widgets(step_id: str, *, keep_branch: bool = False) -> None:
    branch_key = f"branch_{step_id}"
    for key in list(st.session_state):
        if key == branch_key and keep_branch:
            continue
        if key == branch_key or key.startswith(f"note_{step_id}") or key.startswith(f"{step_id}_"):
            del st.session_state[key]


def reset_workflow() -> None:
    st.session_state.step_index = 0
    st.session_state.completed = {}
    st.session_state.observations = []
    st.session_state.step_branches = {}
    st.session_state.notes = {}
    for key in list(st.session_state):
        if is_transient_widget_key(key):
            del st.session_state[key]


def start_workflow(workflow: str) -> None:
    st.session_state.workflow_key = workflow
    reset_workflow()
    st.session_state.page = "guide"
    request_scroll_to_top()
    st.rerun()


def current_workflow_steps(workflow: dict) -> list[dict]:
    steps = workflow["steps"]
    if (
        st.session_state.get("sorting_device") != "selector"
        or st.session_state.workflow_key not in {"analysis", "sorting"}
    ):
        return steps

    selector_steps = list(steps)

    # No.370: Selectorでは、元のSTEP 15（Apply SampleしてRun）を
    # 元のSTEP 10（レーザーアライメント）とSTEP 11の間へ移動する。
    apply_sample_step = next(
        (step for step in selector_steps if step.get("id") == "a11"),
        None,
    )
    if apply_sample_step is not None:
        selector_steps.remove(apply_sample_step)
        laser_index = next(
            (i for i, step in enumerate(selector_steps) if step.get("id") == "a10"),
            None,
        )
        if laser_index is not None:
            selector_steps.insert(laser_index + 1, apply_sample_step)

    # No.367 / No.382 / No.383: Selectorの元のSTEP 5とSTEP 6の間へ
    # 分注機のディスペンシングパラメータ書き換え工程を追加する。
    parameter_step = {
        "id": "selector_dispensing_parameters",
        "title": "ディスペンシングパラメータの書き換え",
        "instruction": (
            "分注機のパラメーターの書き換えをおこないます。 "
            "※サンプル特徴が前回と同じ内容なら本作業は不要"
        ),
        "current_status": "ディスペンシングパラメータを書き換える前の状態です。",
        "task": (
            "分注機のパラメーターの書き換えをおこないます。 "
            "※サンプル特徴が前回と同じ内容なら本作業は不要"
        ),
        "why": "今回のサンプル特徴に合わせて、分注機のディスペンシングパラメータを確認・設定するためです。",
        "checks": [
            "０アドミニストレーターを選択した",
            "メニュー開いた",
            "セット１のタブを選択した",
            "ディスペンシングパラメータに手入力で書き換えた",
        ],
        "check_help": {
            "ディスペンシングパラメータに手入力で書き換えた": (
                "注釈：デスクトップにあるパラメーターリストに基準の数字が入っているので"
                "それに準じて書き換え"
            )
        },
        "ok_state": [
            "０アドミニストレーター、メニュー、セット１の順に設定画面を開いている",
            "デスクトップのパラメーターリストに準じてディスペンシングパラメータを書き換えている",
        ],
        "ng_state": [
            "別のアドミニストレーターまたは別のセットを選択している",
            "デスクトップのパラメーターリストと異なる値を入力している",
        ],
        "show_screen_section": False,
        "show_result_sections": True,
    }
    sample_file_index = next(
        (i for i, step in enumerate(selector_steps) if step.get("id") == "a04"),
        None,
    )
    if sample_file_index is not None:
        selector_steps.insert(sample_file_index + 1, parameter_step)

    # No.388: Selectorの分離・分注ルートでは、No.367/370反映後の
    # STEP 16とSTEP 17の間に、Apply SampleしてRunと同内容の「再度Run」を追加する。
    # バルクルートは全工程数が16未満のため、この番号位置は存在せず対象外。
    if st.session_state.workflow_key == "sorting" and len(selector_steps) >= 17 and apply_sample_step is not None:
        run_again_step = {
            **apply_sample_step,
            "id": "selector_run_again",
            "title": "再度Run",
            "current_status": "「再度Run」を始める前の状態です。",
        }
        selector_steps.insert(16, run_again_step)

    return selector_steps


def open_dg_setup() -> None:
    # No.379: ドロップレット作製画面へ入るたびに前回の選択状態を破棄し、
    # 装置選択からやり直せる初期状態に戻す。
    st.session_state.dg_device = ""
    st.session_state.dg_chip = ""
    st.session_state.dg_product = ""
    st.session_state.page = "dg_setup"
    request_scroll_to_top()
    st.rerun()


def open_sorting_setup() -> None:
    st.session_state.sorting_device = ""
    st.session_state.sorting_purpose = ""
    st.session_state.page = "sorting_setup"
    request_scroll_to_top()
    st.rerun()


def open_recovery_setup() -> None:
    # No.389: 「サンプルを取り出す」へ入るたびに前回のルート選択を破棄する。
    st.session_state.recovery_method = ""
    st.session_state.page = "recovery_setup"
    request_scroll_to_top()
    st.rerun()


def save_observation(step_id: str, status: str) -> None:
    st.session_state.observations.append(
        {
            "time": datetime.now().isoformat(timespec="seconds"),
            "step_id": step_id,
            "status": status,
        }
    )


def go(page: str) -> None:
    st.session_state.page = page
    request_scroll_to_top()
    st.rerun()


def open_experiment_records() -> None:
    current_page = str(st.session_state.get("page", "home"))
    if current_page != "experiment_records":
        st.session_state.experiment_record_return_page = current_page
    st.session_state.page = "experiment_records"
    request_scroll_to_top()
    st.rerun()


def apply_query_navigation() -> None:
    device = str(st.query_params.get("account_setup", "")).strip().lower()
    if device in {"selector", "sort"}:
        st.session_state.page = "account_setup"
        st.session_state.account_setup_device = device
    elif st.session_state.page == "account_setup":
        st.session_state.page = "guide"


def open_results(step_key: str = "") -> None:
    st.session_state.result_step = step_key
    st.session_state.page = "results"
    request_scroll_to_top()
    st.rerun()


def html_lines(text: str) -> str:
    return html.escape(str(text)).replace("\n", "<br>")


def product_hover_card_html(product: dict) -> str:
    attributes = "".join(
        f'<span class="product-hover-card-attribute"><b>'
        f'{html.escape(str(item.get("label", "")))}</b><br>'
        f'{html_lines(item.get("value", ""))}</span>'
        for item in product.get("attributes", [])
    )
    product_number = str(product.get("product_number", ""))
    image_filename = PRODUCT_IMAGE_BY_NUMBER.get(product_number, "")
    image_uri = (
        product_image_data_uri(str(PRODUCT_IMAGE_DIR / image_filename))
        if image_filename
        else ""
    )
    if image_uri:
        product_name = " ".join(str(product.get("product_name", "")).split())
        body = (
            '<span class="product-hover-card-body has-image">'
            f'<span class="product-hover-card-attributes">{attributes}</span>'
            '<span class="product-hover-card-image-wrap">'
            f'<img class="product-hover-card-image" src="{image_uri}" '
            f'alt="{html.escape(product_name)}" loading="lazy" decoding="async">'
            '</span></span>'
        )
    else:
        body = attributes
    return (
        '<span class="product-hover-card" role="tooltip">'
        f'<span class="product-hover-card-category">{html.escape(str(product.get("group", "")))}｜'
        f'{html.escape(str(product.get("category", "")))}</span>'
        f'<span class="product-hover-card-title">{html_lines(product.get("product_name", ""))}</span>'
        f'<span class="product-hover-card-number">製品番号：'
        f'{html.escape(product_number)}</span>'
        f'{body}</span>'
    )


def product_hover_span_html(display_name: str, official_name: str) -> str:
    """Render a non-clickable, mouse-hover-only product reference."""
    product = PRODUCT_NAME_INDEX.get(official_name)
    if not product:
        return html.escape(display_name)
    return (
        f'<span class="product-hover-ref" '
        f'aria-label="{html.escape(display_name)}の製品情報">'
        f'{html.escape(display_name)}{product_hover_card_html(product)}</span>'
    )


def product_hover_text_html(text: str) -> str:
    """Add product-catalog hover cards to exact product names in one label."""
    source = str(text)
    spans = find_product_name_spans(source, PRODUCT_NAME_INDEX)
    if not spans:
        return html.escape(source)
    parts: list[str] = []
    cursor = 0
    for start, end, product in spans:
        parts.append(html.escape(source[cursor:start]))
        official_name = str(product.get("product_name", source[start:end]))
        parts.append(product_hover_span_html(source[start:end], official_name))
        cursor = end
    parts.append(html.escape(source[cursor:]))
    return "".join(parts)


def guide_checkbox(
    text: str,
    *,
    value: bool,
    key: str,
) -> bool:
    """Render standard checkboxes, adding catalog hover only when a product name matches."""
    if not find_product_name_spans(str(text), PRODUCT_NAME_INDEX):
        return st.checkbox(text, value=value, key=key)
    check_col, label_col = st.columns([1, 30], gap="small")
    with check_col:
        checked = st.checkbox(
            text,
            value=value,
            key=key,
            label_visibility="collapsed",
        )
    with label_col:
        st.markdown(
            f'<div class="prep-check-row">{product_hover_text_html(text)}</div>',
            unsafe_allow_html=True,
        )
    return checked


def oil_mixing_note_html() -> str:
    five_percent = product_hover_span_html(
        "008-FluoroSurfactant-5wtH-10mL",
        "008-FluoroSurfactant-5wtH-10mL",
    )
    point_one_percent = product_hover_span_html(
        "008-FluoroSurfactant-0.1wtH-100mL",
        "008-FluoroSurfactant-0.1wtH-100mL",
    )
    return (
        '<div class="help-box">Oilは界面活性剤が5%含有（' + five_percent +
        ' ）と0.1%含有（' + point_one_percent +
        ' ）のオイルを2:3の比率で希釈し、約2%にして使用してください。</div>'
    )


def render_sop_guidance(*, show_details: bool = False) -> None:
    st.markdown(
        f'<div class="sop-notice">{html.escape(DATA["sop_notice"])}</div>',
        unsafe_allow_html=True,
    )
    if show_details:
        st.markdown(
            '<details class="sop-details"><summary>SOPとは？</summary>'
            '<div>SOPは、施設または研究室で定められた標準作業手順書です。'
            'ナビと内容が異なる場合は、施設SOPを優先してください。</div></details>',
            unsafe_allow_html=True,
        )


def image_placeholder(
    filename: str,
    title: str,
    *,
    caption: str = "",
    show_title: bool = True,
) -> None:
    path = IMAGE_DIR / filename
    if show_title:
        st.markdown(f"#### {html.escape(title)}")
    if path.is_file():
        st.image(str(path), use_container_width=True)
    else:
        safe_title = html.escape(title)
        safe_filename = html.escape(filename)
        st.markdown(
            f'<div class="image-placeholder"><div style="font-size:2.2rem">📷</div>'
            f'<div style="font-size:1.25rem;font-weight:800">{safe_title}</div>'
            f'<div style="margin-top:.8rem"><code>{safe_filename}</code></div>'
            f'<div style="margin-top:.8rem">を<br><b>imagesフォルダ</b>へ配置してください</div></div>',
            unsafe_allow_html=True,
        )
    if caption:
        st.markdown(
            f'<div class="result-source">{html.escape(caption)}</div>',
            unsafe_allow_html=True,
        )


def show_ok_ng(ok_items, ng_items, active, ok_images=None, ng_images=None) -> None:
    if ok_items is None:
        ok_items = ["工程の確認項目をすべて満たしている"]
    if ng_items is None:
        ng_items = ["異常がないことを確認してください。"]

    st.markdown('<div class="section-title">✅ OK例</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ok-box">' + "<br>".join(f"・{html_lines(x)}" for x in ok_items) + "</div>",
        unsafe_allow_html=True,
    )
    for img in ok_images or []:
        image_placeholder(img["filename"], img.get("title", "OK例"))

    st.markdown('<div class="section-title">❌ NG例</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ng-box">' + "<br>".join(f"・{html_lines(x)}" for x in ng_items) + "</div>",
        unsafe_allow_html=True,
    )
    for img in ng_images or []:
        image_placeholder(img["filename"], img.get("title", "NG例"))

    render_abnormal(active)


def render_sidebar_footer() -> None:
    st.markdown(
        f'''<div class="sidebar-footer">
        <div class="product-name">On-Chip OpeR</div>
        <div>ナビゲーションアプリ：{html.escape(VERSION)}</div>
        <div style="margin-top:.55rem">{html.escape(COMPANY_NAME)}</div>
        <div>© 2026 {html.escape(COMPANY_NAME)}</div>
        <div>All Rights Reserved.</div>
        </div>''',
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=True)
        st.header("実験ナビゲーション")
        if st.session_state.page != "home":
            if st.button("← 最初の画面に戻る", use_container_width=True):
                st.query_params.clear()
                go("home")

        if st.session_state.page in {"guide", "complete"}:
            workflow = DATA["workflows"][st.session_state.workflow_key]
            steps = current_workflow_steps(workflow)
            idx = min(st.session_state.step_index, len(steps) - 1)
            completed_count = sum(bool(st.session_state.completed.get(step["id"])) for step in steps)

            st.caption(workflow["label"])
            st.progress(completed_count / max(len(steps), 1))
            st.write(f"進捗：{completed_count} / {len(steps)}")
            if st.session_state.page == "complete":
                st.caption("現在：完了")
            else:
                st.caption(f"現在：Step {idx + 1} / {len(steps)}")

            if st.button(
                "実験記録",
                use_container_width=True,
                key=f"sidebar_workflow_experiment_records_{st.session_state.workflow_key}",
            ):
                open_experiment_records()

            with st.expander("工程一覧", expanded=True):
                for n, step in enumerate(steps):
                    mark = "✓ " if st.session_state.completed.get(step["id"]) else ""
                    current = st.session_state.page == "guide" and n == idx
                    key_prefix = "sidebar_step_current" if current else "sidebar_step"
                    if st.button(
                        f'{mark}Step {n + 1}　{step["title"]}',
                        key=f"{key_prefix}_{st.session_state.workflow_key}_{n}",
                        use_container_width=True,
                    ):
                        st.session_state.step_index = n
                        st.session_state.page = "guide"
                        request_scroll_to_top()
                        st.rerun()

        else:
            st.caption("メニュー")
            if st.session_state.get("layout_mode", "beginner") != "master":
                if st.button(
                    "ドロップレットを作る",
                    use_container_width=True,
                    key="sidebar_menu_beginner",
                ):
                    open_dg_setup()
                if st.button("ソーティング・分注を行う", use_container_width=True, key="sidebar_menu_sorting"):
                    open_sorting_setup()
                if st.button(
                    "ドロップレットから取り出す",
                    use_container_width=True,
                    key="sidebar_menu_recovery",
                ):
                    open_recovery_setup()
            if st.button(
                "実験条件検討",
                use_container_width=True,
                key="sidebar_menu_experiment",
            ):
                go("experiment_condition_advisor")
            if st.button(
                "実験記録",
                use_container_width=True,
                key="sidebar_menu_experiment_records",
            ):
                open_experiment_records()
            if st.button("測定結果を確認する", use_container_width=True, key="sidebar_menu_results"):
                open_results()
            if st.button("トラブルを解決する", use_container_width=True, key="sidebar_menu_trouble"):
                go("trouble")
            if st.session_state.page != "home":
                if st.button("用語集", use_container_width=True, key="sidebar_menu_glossary"):
                    go("glossary")
                if st.button("製品一覧", use_container_width=True, key="sidebar_menu_products"):
                    go("products")

            if st.session_state.page == "home":
                render_joint_ai_sidebar()

        render_sidebar_footer()


def joint_ai_wordmark_html(*, compact: bool = False) -> str:
    """Return the shared JointAI wordmark markup."""
    classes = "joint-ai-wordmark compact" if compact else "joint-ai-wordmark"
    return (
        f'<div class="{classes}">'
        '<span class="joint-ai-spark">✦</span>'
        '<span class="joint-ai-joint">Joint</span>'
        '<span class="joint-ai-ai">AI</span>'
        '</div>'
    )


def render_selection_choice_image(
    filename: str,
    alt_text: str,
    *,
    compact: bool = False,
) -> None:
    """Render an existing product-catalog image in a selection card."""
    image_uri = product_image_data_uri(str(PRODUCT_IMAGE_DIR / filename))
    if not image_uri:
        return
    classes = "selection-choice-image chip" if compact else "selection-choice-image"
    st.markdown(
        f'<div class="{classes}"><img src="{image_uri}" '
        f'alt="{html.escape(alt_text)}" loading="lazy" decoding="async"></div>',
        unsafe_allow_html=True,
    )


def render_fluorescence_wavelength_figure() -> None:
    """Render the wavelength and detection-channel overview as an image."""
    figure_path = IMAGE_DIR / "fluorescence_wavelength_channels.png"
    if not figure_path.is_file():
        figure_path = IMAGE_DIR / "fluorescence_wavelength_channels.svg"
    if figure_path.is_file():
        st.image(str(figure_path), use_container_width=True)


def home_card(
    title: str,
    body: str,
    *,
    row: str,
    badge: str = "",
    badge_kind: str = "available",
) -> None:
    badge_classes = "home-availability-badge"
    card_classes = f"home-card {row}"
    if badge:
        card_classes += " has-badge"
    if badge_kind == "paid":
        badge_classes += " home-paid-badge"
    elif badge_kind == "unavailable":
        badge_classes += " home-unavailable-badge"
        card_classes += " home-card-unavailable"
    badge_html = (
        f'<span class="{badge_classes}">{html.escape(badge)}</span>'
        if badge
        else ""
    )
    st.markdown(
        f'<div class="{card_classes}"><div class="home-card-header"><h3>{title}</h3></div>{body}{badge_html}</div>',
        unsafe_allow_html=True,
    )


def render_joint_ai_overview() -> None:
    """Render the polished JointAI concept overview on the home JointAI panel."""
    st.markdown(
        '''
        <div class="joint-ai-overview"><b>JointAIとは</b>
        JointAIは、<strong>On-Chip OpeRが蓄積する実験知識と、各施設が利用するAIの知識を「Joint＝つなぐ」ための対話・監督機能</strong>です。両者を一体化するのではなく、それぞれが独立したまま、判断に必要な情報だけを問い合わせ合うことを基本とします。<br><br>
        施設側AIが判断材料を求めたときは、OpeRが持つ操作手順、実験条件、製品情報、過去の実験結果、トラブル事例などから、許可された情報を提供します。反対にOpeR側の実績が不足している場合は、施設側AIへ施設内の知見を確認できます。AIが出した回答はそのまま利用者へ渡さず、<strong>引用元、根拠の種類と強さ、未確認事項</strong>を確認し、根拠が弱ければその理由を明記した回答へ整えることを目指します。<br><br>
        質問、やり取り、引用元、最終回答、その後の実験結果を蓄積することで、OpeR側には使うほど実験ライブラリーが育ちます。一定期間ごとに蓄積情報を整理して接続先AIへ提示し、過去の知見を活用しやすくする運用も想定しています。<br><br>
        また、施設が将来別の主要AIへ移行しても、Joint先を切り替えることで、<strong>OpeR側に残した実験知識を新しいAIでも継続して活用</strong>できます。特定のAI製品に知識を閉じ込めず、必要な情報だけを受け渡す設計を基本とし、施設の方針に応じてローカルネットワーク中心の運用も想定します。</div>
        ''',
        unsafe_allow_html=True,
    )


def render_joint_ai_sidebar() -> None:
    """Render the collapsible JointAI controls while preserving the wordmark."""
    expanded = bool(st.session_state.get("joint_ai_sidebar_expanded", False))
    title_col, toggle_col = st.columns([6, 1], gap="small")
    with title_col:
        st.markdown(
            f'<div class="joint-ai-sidebar-heading">{joint_ai_wordmark_html()}</div>',
            unsafe_allow_html=True,
        )
    with toggle_col:
        if st.button(
            "▾" if expanded else "▸",
            key="joint_ai_sidebar_toggle",
            help="JointAIを閉じる" if expanded else "JointAIを開く",
            use_container_width=True,
        ):
            st.session_state.joint_ai_sidebar_expanded = not expanded
            st.rerun()

    if expanded:
        sidebar_question = st.text_area(
            "自由質問",
            placeholder="On-Chip装置や実験ナビについて質問を入力してください。",
            height=88,
            key="joint_ai_sidebar_question",
        )
        st.markdown(
            '<div class="joint-ai-sidebar-guide">参考資料をここにドラッグ＆ドロップするか、ファイルを選択し、質問してください。</div>',
            unsafe_allow_html=True,
        )
        uploaded_files = st.file_uploader(
            "参考資料をここにドラッグ＆ドロップするか、ファイルを選択し、質問してください。",
            type=["pdf", "docx", "txt", "md", "csv", "json", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="joint_ai_file_upload",
            label_visibility="collapsed",
        )
        metadata = [
            {
                "name": uploaded.name,
                "type": uploaded.type or "",
                "size": int(uploaded.size),
            }
            for uploaded in (uploaded_files or [])
        ]
        st.session_state["joint_ai_uploaded_metadata"] = metadata
        if metadata:
            st.caption(f"選択中の参考資料：{len(metadata)}件")

        if st.button(
            "質問する",
            type="primary",
            use_container_width=True,
            key="joint_ai_sidebar_ask",
        ):
            question = sidebar_question.strip()
            if not question:
                st.warning("質問を入力してください。")
            else:
                context = {
                    "page": "home",
                    "system": "On-Chip OpeR",
                    "reference_files": metadata,
                }
                response = JOINT_AI_CONNECTOR.ask(question=question, context=context)
                st.session_state["joint_ai_question_home"] = question
                st.session_state["joint_ai_response_home"] = response.to_dict()
                st.session_state["joint_ai_home_open"] = True
                st.rerun()

        st.caption(
            "現在はダミー接続のため、選択した資料の本文解析はまだ行いません。"
        )

    if st.button("用語集", use_container_width=True, key="sidebar_glossary_open"):
        go("glossary")
    if st.button("製品一覧", use_container_width=True, key="sidebar_products_open"):
        go("products")


def render_layout_mode_switch() -> None:
    """Render the home layout selector without persisting beyond the session."""
    current = str(st.session_state.get("layout_mode", "beginner"))
    st.markdown('<div class="layout-mode-switch-spacer"></div>', unsafe_allow_html=True)
    beginner_col, divider_col, master_col = st.columns([1.0, 0.10, 1.0], gap="small")
    with beginner_col:
        if st.button(
            "ビギナーズレイアウト",
            type="primary" if current == "beginner" else "secondary",
            use_container_width=False,
            key="layout_mode_beginner",
        ):
            if current != "beginner":
                st.session_state.layout_mode = "beginner"
                st.rerun()
    with divider_col:
        st.markdown('<div class="layout-mode-divider">｜</div>', unsafe_allow_html=True)
    with master_col:
        if st.button(
            "マスターレイアウト",
            type="primary" if current == "master" else "secondary",
            use_container_width=False,
            key="layout_mode_master",
        ):
            if current != "master":
                st.session_state.layout_mode = "master"
                st.rerun()


def render_home_operation_cards() -> None:
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        home_card(
            "ドロップレットを作る",
            """
        <div class="home-models"><strong>対応機種</strong><br>On-chip Droplet Generator<br>On-chip Droplet Generator S</div>
        <p class="home-purpose">W/Oドロップレット・ゲルマイクロドロップ（GMD）作製</p>
        <div class="home-first-use-note">初めてご使用になる方は、事前に実験条件の検討をお済ませのうえ、ご使用いただくことをおすすめします。</div>""",
            row="top",
        )
        if st.button("ドロップレットを作製する", type="primary", use_container_width=True, key="home_start_beginner"):
            open_dg_setup()
    with c2:
        home_card(
            "ソーティング・分注を行う",
            """
        <div class="home-models"><strong>対応機種</strong><br>On-chip Droplet Selector<br>On-chip Sort</div>
        <p class="home-purpose">サンプル解析・分離・分注</p>
        <div class="home-first-use-note">初めて装置を使用する方は、先に「測定結果を確認する」をお読みください。</div>""",
            row="top",
        )
        if st.button("ソーティング・分注を行う", type="primary", use_container_width=True, key="home_start_sorting"):
            open_sorting_setup()
    with c3:
        home_card(
            "ドロップレットから取り出す",
            """
        <div class="home-models"><strong>方法</strong><br>手作業：Droplet Generator付属プラズマボール<br>自動：On-chip Droplet Work Station</div>
        <p class="home-purpose">分注済みドロップレットからサンプルを解放</p>""",
            row="top",
        )
        if st.button(
            "サンプルを取り出す",
            type="primary",
            use_container_width=True,
            key="home_start_recovery",
        ):
            open_recovery_setup()


def render_home_support_cards() -> None:
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        home_card(
            "実験条件検討",
            "<p>実験目的、封入対象、培地・粘度、目標液滴、後工程を入力し、閉域の試作エンジンで見解とPDFを作成します。</p>",
            row="bottom",
        )
        if st.button(
            "実験条件を検討する",
            use_container_width=True,
            key="home_open_experiment",
        ):
            go("experiment_condition_advisor")
    with c2:
        home_card(
            "測定結果を確認する",
            "<ul class='home-feature-list'><li>フローサイトメーターの原理</li><li>各種のプロットの見方</li><li>その他の測定結果を読み解くための機能解説</li></ul><p class='home-status'><span style='font-size:.88rem;font-weight:600'>JointAI解析は準備中</span></p>",
            row="bottom",
        )
        if st.button("プロット解説を見る", use_container_width=True, key="home_open_results"):
            open_results()
    with c3:
        home_card(
            "トラブルを解決する",
            "<p>エラーや異常が発生した際、症状から確認項目と対応候補を探します。</p>",
            row="bottom",
        )
        if st.button("トラブルを解決する", use_container_width=True, key="home_open_trouble"):
            go("trouble")


def render_home() -> None:
    master_layout = st.session_state.get("layout_mode", "beginner") == "master"

    title_col, mode_col = st.columns([5.2, 2.0], gap="medium", vertical_alignment="top")
    with title_col:
        st.title("On-Chip OpeR")
        st.caption(f"最新版 {VERSION}｜AI×オペレーティングシステムによる対話型実行支援システム")
    with mode_col:
        render_layout_mode_switch()

    heading_col, joint_ai_col = st.columns([5.4, 1.2], vertical_alignment="center")
    with heading_col:
        st.markdown("## 実験を始めますか？")
    with joint_ai_col:
        if (
            not master_layout
            and JOINT_AI_CONNECTOR.enabled
            and st.button(
                "✦ JointAI",
                use_container_width=True,
                key="home_joint_ai_toggle",
            )
        ):
            st.session_state["joint_ai_home_open"] = not bool(
                st.session_state.get("joint_ai_home_open", False)
            )
            st.rerun()

    render_home_joint_ai_assistant(
        force_open=master_layout,
        master_layout=master_layout,
    )
    if not master_layout:
        render_sop_guidance(show_details=True)
        st.markdown('<div class="home-lead">現在の準備状況に応じたエントリーを選んでください。</div>', unsafe_allow_html=True)

    if master_layout:
        render_home_support_cards()
        st.markdown("<div style='height:.55rem'></div>", unsafe_allow_html=True)
        render_home_operation_cards()
    else:
        render_home_operation_cards()
        st.markdown("<div style='height:.55rem'></div>", unsafe_allow_html=True)
        render_home_support_cards()


def render_dg_setup() -> None:
    st.title("ドロップレットを作る")
    st.info(
        "ドロップレット作製では、使用する試料や溶液の粘度・濃度によって、作製条件や結果に影響する場合があります。"
        "初めて使用する試料や条件で作製される場合は、事前に「実験条件検討」ページをご確認いただき、"
        "適切な条件を検討してから操作を開始されることをおすすめします。"
    )
    if st.button(
        "実験条件検討ページを見る",
        key="dg_open_experiment_condition_advisor",
    ):
        go("experiment_condition_advisor")
    st.write("装置、流路系、作製するものを上から順番に選択してください。選択後、該当するマニュアルに沿った工程を開始します。")

    st.markdown('<div class="step-title"><b>① 使用する装置を選ぶ</b></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            render_selection_choice_image(
                "droplet_generator.webp",
                "On-chip Droplet Generator",
            )
            if st.button(
                "On-chip Droplet Generator",
                type="primary" if st.session_state.dg_device == "generator" else "secondary",
                use_container_width=True,
                key="dg_select_generator",
            ):
                if st.session_state.dg_device != "generator":
                    st.session_state.dg_device = "generator"
                    st.session_state.dg_chip = ""
                    st.session_state.dg_product = ""
                st.rerun()
    with c2:
        with st.container(border=True):
            render_selection_choice_image(
                "droplet_generator_s.webp",
                "On-chip Droplet Generator S",
            )
            if st.button(
                "On-chip Droplet Generator S",
                type="primary" if st.session_state.dg_device == "generator_s" else "secondary",
                use_container_width=True,
                key="dg_select_generator_s",
            ):
                if st.session_state.dg_device != "generator_s":
                    st.session_state.dg_device = "generator_s"
                    st.session_state.dg_chip = ""
                    st.session_state.dg_product = ""
                st.rerun()

    if not st.session_state.dg_device:
        st.info("最初に使用する装置を選択してください。")
        return

    if st.session_state.dg_device == "generator":
        st.markdown('<div class="step-title"><b>② 使用する流路チップを選ぶ</b></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        chip_options = [
            ("800", "2D Chip-800DG"),
            ("1060_1100", "2D Chip-1060DG or 2D Chip-1100DG"),
        ]
        chip_images = {
            "800": "2d_chip_800dg.webp",
            "1060_1100": "2d_chip_1060_1100dg.webp",
        }
        for col, (value, label) in zip((c1, c2), chip_options):
            with col:
                with st.container(border=True):
                    render_selection_choice_image(
                        chip_images[value],
                        label,
                        compact=True,
                    )
                    if st.button(
                        label,
                        type="primary" if st.session_state.dg_chip == value else "secondary",
                        use_container_width=True,
                        key=f"dg_select_chip_{value}",
                    ):
                        st.session_state.dg_chip = value
                        st.session_state.dg_product = ""
                        st.rerun()
        chip_labels = {
            "800": "2D Chip-800DG",
            "1060_1100": "2D Chip-1060DG or 2D Chip-1100DG",
        }
    else:
        st.markdown('<div class="step-title"><b>② 使用するチップホルダーを選ぶ</b></div>', unsafe_allow_html=True)
        st.caption("Droplet Generator Sの製品仕様に合わせ、作製径に対応するホルダーを選択してください。")
        c1, c2 = st.columns(2)
        holder_options = [
            ("dgs_a", "2液混合 Chip Holder（35～45 µm）"),
            ("dgs_b", "DG1 Chip Holder（60～120 µm）"),
        ]
        for col, (value, label) in zip((c1, c2), holder_options):
            with col:
                with st.container(border=True):
                    st.markdown(f"**{label}**")
                    if st.button(
                        "このホルダーを選ぶ",
                        type="primary" if st.session_state.dg_chip == value else "secondary",
                        use_container_width=True,
                        key=f"dg_select_holder_{value}",
                    ):
                        st.session_state.dg_chip = value
                        st.session_state.dg_product = ""
                        st.rerun()
        chip_labels = {
            "dgs_a": "2液混合 Chip Holder（35～45 µm）",
            "dgs_b": "DG1 Chip Holder（60～120 µm）",
        }

    if not st.session_state.dg_chip:
        st.info("使用する流路系を選択してください。")
        return

    st.markdown('<div class="step-title"><b>③ 作りたいものを選ぶ</b></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "W/Oドロップレットを選ぶ",
            type="primary" if st.session_state.dg_product == "wo" else "secondary",
            use_container_width=True,
            key="dg_select_product_wo",
        ):
            st.session_state.dg_product = "wo"
            st.rerun()
    with c2:
        if st.button(
            "GMDを選ぶ",
            type="primary" if st.session_state.dg_product == "gmd" else "secondary",
            use_container_width=True,
            key="dg_select_product_gmd",
        ):
            st.session_state.dg_product = "gmd"
            st.rerun()

    if not st.session_state.dg_product:
        st.info("作製するものを選択してください。")
        return

    product_labels = {"wo": "W/Oドロップレット", "gmd": "GMD"}
    device_label = (
        "On-chip Droplet Generator"
        if st.session_state.dg_device == "generator"
        else "On-chip Droplet Generator S"
    )
    flow_label = "流路チップ" if st.session_state.dg_device == "generator" else "チップホルダー"
    st.markdown(
        '<div class="dg-summary"><b>選択内容</b><br>'
        f'装置：{html.escape(device_label)}<br>'
        f'{flow_label}：{html.escape(chip_labels[st.session_state.dg_chip])}<br>'
        f'作製するもの：{html.escape(product_labels[st.session_state.dg_product])}</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.dg_device == "generator":
        if st.session_state.dg_product == "gmd" and st.session_state.dg_chip == "1060_1100":
            st.warning("GMDのサンプル調製・ゲル化・回収はGMD作製プロトコルを、装置接続・チップ操作・初期圧力は1060DG／1100DGマニュアルを根拠に案内します。")
        workflow_map = {
            ("800", "wo"): "dg800_wo",
            ("800", "gmd"): "dg800_gmd",
            ("1060_1100", "wo"): "dg1060_1100_wo",
            ("1060_1100", "gmd"): "dg1060_1100_gmd",
        }
    else:
        if st.session_state.dg_product == "gmd":
            st.warning("Droplet Generator SでGMDを作製する場合は、温調観察ユニットを備えるTタイプを前提に案内します。")
        workflow_map = {
            ("dgs_a", "wo"): "dgs_a_wo",
            ("dgs_a", "gmd"): "dgs_a_gmd",
            ("dgs_b", "wo"): "dgs_b_wo",
            ("dgs_b", "gmd"): "dgs_b_gmd",
        }

    if st.button("この条件で工程を開始する", type="primary", use_container_width=True, key="dg_start_selected_workflow"):
        start_workflow(workflow_map[(st.session_state.dg_chip, st.session_state.dg_product)])


def render_sorting_setup() -> None:
    st.title("ソーティング・分注を行う")
    st.info(
        "ソーティング・分注を行う際は、フローサイトメーターやプロットの見方についての基礎知識が、"
        "操作や実験結果を適切に判断するうえで重要となります。操作にまだ慣れていない場合は、"
        "試薬や消耗品を有効にお使いいただくためにも、事前に「プロット解説」を十分にご確認いただき、"
        "シミュレーション問題をクリアしてから操作を開始されることをおすすめします。"
    )
    if st.button(
        "プロット解説ページを見る",
        key="sorting_open_plot_guide",
    ):
        open_results()
    st.write("使用する装置を選択してください。On-chip Droplet Selectorを選んだ場合は、続けて分離方法を選択します。")

    st.markdown('<div class="step-title"><b>① 使用する装置を選ぶ</b></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            render_selection_choice_image(
                "droplet_selector.webp",
                "On-chip Droplet Selector",
            )
            if st.button(
                "On-chip Droplet Selector",
                type="primary" if st.session_state.sorting_device == "selector" else "secondary",
                use_container_width=True,
                key="sorting_select_device_selector",
            ):
                st.session_state.sorting_device = "selector"
                st.session_state.sorting_purpose = ""
                st.rerun()
    with c2:
        with st.container(border=True):
            render_selection_choice_image(
                "onchip_sort.webp",
                "On-chip Sort",
            )
            if st.button(
                "On-chip Sort",
                type="primary" if st.session_state.sorting_device == "sort" else "secondary",
                use_container_width=True,
                key="sorting_select_device_sort",
            ):
                st.session_state.sorting_device = "sort"
                st.session_state.sorting_purpose = ""
                start_workflow("analysis")

    if not st.session_state.sorting_device:
        st.info("最初に使用する装置を選択してください。")
        return

    if st.session_state.sorting_device != "selector":
        return

    st.markdown('<div class="step-title"><b>② 分離方法を選ぶ</b></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    purpose_options = [
        ("dispense", "分離・分注"),
        ("bulk", "分離（バルクソーティング）"),
    ]
    for col, (value, label) in zip((c1, c2), purpose_options):
        with col:
            if st.button(
                label,
                type="primary" if st.session_state.sorting_purpose == value else "secondary",
                use_container_width=True,
                key=f"sorting_select_purpose_{value}",
            ):
                st.session_state.sorting_purpose = value
                st.rerun()

    if not st.session_state.sorting_purpose:
        st.info("行いたい分離方法を選択してください。")
        return

    purpose_labels = {
        "dispense": "分離・分注",
        "bulk": "分離（バルクソーティング）",
    }
    st.markdown(
        '<div class="dg-summary"><b>選択内容</b><br>'
        '装置：On-chip Droplet Selector<br>'
        f'目的：{html.escape(purpose_labels[st.session_state.sorting_purpose])}</div>',
        unsafe_allow_html=True,
    )

    if st.button("この条件で工程を開始する", type="primary", use_container_width=True, key="sorting_start_selected_workflow"):
        workflow = "sorting" if st.session_state.sorting_purpose == "dispense" else "analysis"
        start_workflow(workflow)



def render_recovery_setup() -> None:
    st.title("ドロップレットから取り出す")
    st.write(
        "取り出し方法を選択してください。どちらの方法も、分注済みプレートへ培地入りの空ドロップレットを加え、"
        "電気処理でドロップレットを壊して内容物を培地相へ戻す流れです。"
    )

    st.markdown('<div class="step-title"><b>① 取り出し方法を選ぶ</b></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        with st.container(border=True):
            st.markdown('<div class="recovery-choice-marker"></div>', unsafe_allow_html=True)
            render_selection_choice_image(
                "droplet_generator.webp",
                "Droplet Generator付属プラズマボール",
            )
            st.markdown('<div class="recovery-choice-title">手作業（Droplet Generator付属プラズマボール）</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="recovery-choice-note">ピペット等で空ドロップレットを全ウェルへ加え、プラズマボールで均等に電気をかけます。</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "手作業を選ぶ",
                type="primary" if st.session_state.recovery_method == "manual" else "secondary",
                use_container_width=True,
                key="recovery_select_manual",
            ):
                st.session_state.recovery_method = "manual"
                st.rerun()

    with c2:
        with st.container(border=True):
            st.markdown('<div class="recovery-choice-marker"></div>', unsafe_allow_html=True)
            image_c1, image_c2 = st.columns(2, gap="small")
            with image_c1:
                render_selection_choice_image(
                    "onchip_microdispenser.webp",
                    "On-chip Droplet Microdispenser",
                    compact=True,
                )
            with image_c2:
                render_selection_choice_image(
                    "onchip_merge.webp",
                    "On-chip Merge",
                    compact=True,
                )
            st.markdown('<div class="recovery-choice-title">On-chip Droplet Work Station</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="recovery-choice-note">Droplet Microdispenserで空ドロップレットを分注し、On-chip Mergeで破壊・融合処理を行います。</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "Work Stationを選ぶ",
                type="primary" if st.session_state.recovery_method == "workstation" else "secondary",
                use_container_width=True,
                key="recovery_select_workstation",
            ):
                st.session_state.recovery_method = "workstation"
                st.rerun()

    if not st.session_state.recovery_method:
        st.info("最初に取り出し方法を選択してください。")
        return

    manual_selected = ' <span class="recovery-summary-selected">（選択中）</span>' if st.session_state.recovery_method == "manual" else ""
    workstation_selected = ' <span class="recovery-summary-selected">（選択中）</span>' if st.session_state.recovery_method == "workstation" else ""
    st.markdown(
        '<div class="home-models"><strong>方法</strong><br>'
        f'手作業：Droplet Generator付属プラズマボール{manual_selected}<br>'
        f'自動：On-chip Droplet Work Station{workstation_selected}</div>',
        unsafe_allow_html=True,
    )
    if st.button(
        "この方法で工程を開始する",
        type="primary",
        use_container_width=True,
        key="recovery_start_selected_workflow",
    ):
        workflow = (
            "recovery_manual"
            if st.session_state.recovery_method == "manual"
            else "recovery_workstation"
        )
        start_workflow(workflow)


def render_supplemental_information(active: dict) -> None:
    with st.expander("なぜこの操作を行うのですか？"):
        st.write(active.get("why", "この工程の理由は確認中です。"))

    decision_support = active.get("decision_support", [])
    if decision_support:
        with st.expander("判断の目安"):
            for item in decision_support:
                st.write(f"・{item}")

    glossary = active.get("glossary", {})
    if glossary:
        with st.expander("用語解説"):
            for term, description in glossary.items():
                st.markdown(f"**{term}**  ")
                st.write(description)



def collect_screen_images(active: dict) -> list[dict]:
    images = list(active.get("screen_images", []))
    filenames = {img.get("filename") for img in images}
    if active.get("show_signal_figure") and "signal.png" not in filenames:
        images.append({"filename": "signal.png", "title": "Signal"})
    if active.get("show_compensation_figure"):
        if "compensation_before.png" not in filenames:
            images.append({"filename": "compensation_before.png", "title": "Compensation Before"})
        if "compensation_after.png" not in filenames:
            images.append({"filename": "compensation_after.png", "title": "Compensation After"})
    return images


def render_abnormal(active: dict) -> None:
    st.markdown('<div class="section-title">⚠️ 異常時</div>', unsafe_allow_html=True)
    abnormal = active.get("warning") or active.get("abnormal_action") or DATA["contact"]
    if CONTACT_EMAIL in abnormal:
        abnormal_text = abnormal
    else:
        abnormal_text = f"{abnormal}\n\n{DATA['contact']}"
    st.markdown(f'<div class="warn-box">{html_lines(abnormal_text)}</div>', unsafe_allow_html=True)


def joint_ai_reference_files() -> list[dict]:
    """Return metadata for files selected in the home JointAI drop area."""
    files = st.session_state.get("joint_ai_uploaded_metadata", [])
    if not isinstance(files, list):
        return []
    return [dict(item) for item in files if isinstance(item, dict)]


def render_joint_ai_panel(
    *,
    scope: str,
    context: dict,
    prompts: list[str],
    placeholder: str,
    show_overview: bool = False,
    show_upload: bool = False,
) -> None:
    """Render the provider-independent JointAI question and answer panel."""
    response_key = f"joint_ai_response_{scope}"
    selected_question = ""
    with st.container(border=True):
        st.markdown(joint_ai_wordmark_html(compact=True), unsafe_allow_html=True)
        if show_overview:
            render_joint_ai_overview()
        if show_upload:
            st.markdown(
                '<div class="joint-ai-sidebar-guide">参考資料をここにドラッグ＆ドロップするか、ファイルを選択し、質問してください。</div>',
                unsafe_allow_html=True,
            )
            uploaded_files = st.file_uploader(
                "参考資料をここにドラッグ＆ドロップするか、ファイルを選択し、質問してください。",
                type=["pdf", "docx", "txt", "md", "csv", "json", "png", "jpg", "jpeg"],
                accept_multiple_files=True,
                key="joint_ai_master_file_upload",
                label_visibility="collapsed",
            )
            metadata = [
                {
                    "name": uploaded.name,
                    "type": uploaded.type or "",
                    "size": int(uploaded.size),
                }
                for uploaded in (uploaded_files or [])
            ]
            st.session_state["joint_ai_uploaded_metadata"] = metadata
            context = {**context, "reference_files": metadata}
            if metadata:
                st.caption(f"選択中の参考資料：{len(metadata)}件")
        if not show_upload:
            st.caption(
                "現在はネットワークへ接続せず、JointAIのダミー接続が固定回答を返します。"
            )

        reference_files = context.get("reference_files", [])
        if reference_files:
            names = "<br>".join(
                f"・{html.escape(str(item.get('name', '')))}"
                for item in reference_files
                if isinstance(item, dict) and item.get("name")
            )
            if names:
                st.markdown(
                    '<div class="joint-ai-files"><b>選択中の参考資料</b><br>'
                    + names
                    + "</div>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    "資料名は質問コンテキストに含めますが、現在のダミー接続では本文を解析しません。"
                )

        if not show_upload:
            prompt_columns = st.columns(len(prompts))
            for index, prompt in enumerate(prompts):
                with prompt_columns[index]:
                    if st.button(
                        prompt,
                        use_container_width=True,
                        key=f"joint_ai_prompt_{scope}_{index}",
                    ):
                        selected_question = prompt

        free_question = st.text_input(
            "自由質問",
            placeholder=placeholder,
            key=f"joint_ai_question_{scope}",
        )
        if st.button(
            "質問する",
            type="primary",
            use_container_width=True,
            key=f"joint_ai_ask_{scope}",
        ):
            selected_question = free_question.strip()
            if not selected_question:
                st.warning("質問を入力してください。")

        if selected_question:
            response = JOINT_AI_CONNECTOR.ask(
                question=selected_question,
                context=context,
            )
            st.session_state[response_key] = response.to_dict()

        response_data = st.session_state.get(response_key)
        if isinstance(response_data, dict):
            st.markdown("**JointAIによる参考回答**")
            if response_data.get("success"):
                st.info(str(response_data.get("text", "")))
            else:
                st.error(
                    str(
                        response_data.get(
                            "text", "JointAIから回答を取得できませんでした。"
                        )
                    )
                )
            provider = str(response_data.get("provider", ""))
            model = str(response_data.get("model", ""))
            st.caption(f"接続先：{provider or '-'} ／ モデル：{model or '-'}")

        st.caption(
            "JointAIの回答は参考情報です。工程の完了、チェック、分岐、メモなどは変更しません。"
        )


def render_home_joint_ai_assistant(
    *,
    force_open: bool = False,
    master_layout: bool = False,
) -> None:
    """Render the home-level JointAI panel for the selected layout."""
    if not JOINT_AI_CONNECTOR.enabled:
        return
    if not force_open and not st.session_state.get("joint_ai_home_open", False):
        return
    render_joint_ai_panel(
        scope="home",
        context={
            "page": "home",
            "system": "On-Chip OpeR",
            "reference_files": joint_ai_reference_files(),
        },
        prompts=[
            "このシステムで何ができる？",
            "どこから始めればよい？",
            "選択した資料について聞く",
        ],
        placeholder="実験ナビや選択した資料について質問を入力してください。",
        show_overview=not master_layout,
        show_upload=master_layout,
    )


def render_page_joint_ai_assistant(
    *,
    scope: str,
    context: dict,
    prompts: list[str],
    placeholder: str,
) -> None:
    """Render a read-only JointAI button and panel on an independent page."""
    if not JOINT_AI_CONNECTOR.enabled:
        return

    open_key = f"joint_ai_open_{scope}"
    is_open = bool(st.session_state.get(open_key, False))
    button_col, note_col = st.columns([1.25, 5], vertical_alignment="center")
    with button_col:
        if st.button(
            "✦ JointAI",
            use_container_width=True,
            key=f"joint_ai_toggle_{scope}",
        ):
            st.session_state[open_key] = not is_open
            st.rerun()
    with note_col:
        st.markdown(
            f'<div class="joint-ai-usage-note">{html.escape(JOINT_AI_USAGE_NOTE)}</div>',
            unsafe_allow_html=True,
        )

    if not is_open:
        return

    render_joint_ai_panel(
        scope=scope,
        context={**context, "reference_files": joint_ai_reference_files()},
        prompts=prompts,
        placeholder=placeholder,
    )


def build_joint_ai_context(
    workflow_key: str,
    workflow: dict,
    step: dict,
    active: dict,
    step_index: int,
    step_count: int,
) -> dict:
    """Build read-only context for the current guide step."""
    return {
        "workflow_key": workflow_key,
        "workflow_label": workflow.get("label", ""),
        "workflow_description": workflow.get("description", ""),
        "step_index": step_index + 1,
        "step_count": step_count,
        "step_id": step.get("id", ""),
        "step_title": step.get("title", ""),
        "current_status": active.get("current_status", step.get("current_status", "")),
        "task": active.get("task", active.get("instruction", "")),
        "instruction": active.get("instruction", step.get("instruction", "")),
        "operation_groups": active.get("operation_groups", []),
        "operation_steps": active.get("operation_steps", []),
        "checks": active.get("checks", []),
        "selected_branch": st.session_state.step_branches.get(step.get("id", ""), ""),
        "reference_files": joint_ai_reference_files(),
    }


def render_joint_ai_assistant(
    workflow_key: str,
    workflow: dict,
    step: dict,
    active: dict,
    step_index: int,
    step_count: int,
) -> None:
    """Render the optional read-only JointAI interface for a guide step."""
    if not JOINT_AI_CONNECTOR.enabled:
        return

    branch_scope = st.session_state.step_branches.get(step.get("id", ""), "default")
    scope = f"{workflow_key}_{step.get('id', step_index)}_{branch_scope or 'default'}"
    open_key = f"joint_ai_open_{scope}"
    is_open = bool(st.session_state.get(open_key, False))
    button_col, note_col = st.columns([1.25, 5], vertical_alignment="center")
    with button_col:
        if st.button(
            "✦ JointAI",
            use_container_width=True,
            key=f"joint_ai_toggle_{scope}",
        ):
            st.session_state[open_key] = not is_open
            st.rerun()
    with note_col:
        st.markdown(
            f'<div class="joint-ai-usage-note">{html.escape(JOINT_AI_USAGE_NOTE)}</div>',
            unsafe_allow_html=True,
        )

    if not is_open:
        return

    context = build_joint_ai_context(
        workflow_key,
        workflow,
        step,
        active,
        step_index,
        step_count,
    )
    render_joint_ai_panel(
        scope=scope,
        context=context,
        prompts=[
            "この工程はなぜ必要？",
            "失敗するとどうなる？",
            "この工程の注意点は？",
        ],
        placeholder="この工程について質問を入力してください。",
    )


def render_guide() -> None:
    workflow = DATA["workflows"][st.session_state.workflow_key]
    steps = current_workflow_steps(workflow)
    i = min(st.session_state.step_index, len(steps) - 1)
    step = steps[i]
    active = step
    st.subheader(workflow["label"])
    st.write(workflow["description"])
    step_col, skip_col = st.columns([5, 1.35])
    with step_col:
        st.markdown(
            f'<div class="step-title"><b>Step {i + 1} / {len(steps)}</b><br>'
            f'<span style="font-size:1.2rem">{html.escape(step["title"])}</span></div>',
            unsafe_allow_html=True,
        )
    with skip_col:
        if st.button(
            "この工程をスキップ",
            use_container_width=True,
            key=f'skip_step_{step["id"]}',
        ):
            st.session_state.completed[step["id"]] = True
            if i == len(steps) - 1:
                st.session_state.page = "complete"
            else:
                st.session_state.step_index += 1
            request_scroll_to_top()
            st.rerun()

    current_status = step.get("current_status", "").strip()
    if current_status:
        st.markdown('<div class="section-title">現在の状況</div>', unsafe_allow_html=True)
        st.info(current_status)

    pre_branch_title = step.get("pre_branch_title", "").strip()
    pre_branch_text = step.get("pre_branch_text", "").strip()
    pre_branch_images = step.get("pre_branch_images", [])
    if pre_branch_title or pre_branch_text or pre_branch_images:
        if pre_branch_title:
            st.markdown(
                f'<div class="section-title">{html.escape(pre_branch_title)}</div>',
                unsafe_allow_html=True,
            )
        if pre_branch_text:
            st.markdown(pre_branch_text)
        if pre_branch_images:
            cols = st.columns(min(2, len(pre_branch_images)))
            for idx, img in enumerate(pre_branch_images):
                with cols[idx % len(cols)]:
                    image_placeholder(
                        img["filename"],
                        img.get("title", "実画面"),
                        caption=img.get("caption", ""),
                        show_title=not img.get("hide_title", False),
                    )

    branch_selected = True
    if step.get("branches"):
        st.markdown('<div class="section-title">進め方を選ぶ</div>', unsafe_allow_html=True)
        branch_guidance = step.get("branch_guidance", "").strip()
        if branch_guidance:
            st.markdown(branch_guidance)
        st.markdown("選択してください")
        options = {branch["value"]: branch for branch in step["branches"]}
        previous = st.session_state.step_branches.get(step["id"], "")
        values = list(options)
        st.markdown('<div class="branch-choice-note">選択肢をクリックして進め方を選択してください</div>', unsafe_allow_html=True)
        with st.container(border=True):
            selected = st.radio(
                "選択項目",
                values,
                format_func=lambda value: options[value]["label"],
                index=values.index(previous) if previous in values else None,
                key=f'branch_{step["id"]}',
                label_visibility="collapsed",
            )
        if selected:
            if selected != previous:
                clear_step_widgets(step["id"], keep_branch=True)
                st.session_state.completed.pop(step["id"], None)
            st.session_state.step_branches[step["id"]] = selected
            active = {**step, **options[selected]}
            st.info(active.get("instruction", ""))
        else:
            st.session_state.step_branches.pop(step["id"], None)
            st.session_state.completed.pop(step["id"], None)
            branch_selected = False

    if (
        branch_selected
        and st.session_state.get("sorting_device") == "selector"
        and step.get("id") == "a08"
    ):
        branch_value = st.session_state.step_branches.get(step["id"], "")
        if branch_value.startswith("emulsion_"):
            selector_check = "継ぎ足しカップをセットして、カップの線よりも下までオイルを入れた"
        elif branch_value.startswith("gmd_"):
            selector_check = "継ぎ足しカップをセットして、カップの線よりも下まで培地を入れた"
        else:
            selector_check = ""
        active_checks = list(active.get("checks", []))
        if selector_check and selector_check not in active_checks:
            active = {**active, "checks": [*active_checks, selector_check]}

    st.markdown('<div class="section-title">やること</div>', unsafe_allow_html=True)
    task = active.get("task", active.get("instruction", ""))
    task_html = html_lines(task)
    if step.get("id") == "a03" and st.session_state.workflow_key in {"analysis", "sorting"}:
        account_device = (
            "selector"
            if st.session_state.workflow_key == "sorting"
            or st.session_state.get("sorting_device") == "selector"
            else "sort"
        )
        st.markdown(
            f'<div class="action-box action-box-row"><b>{task_html}</b>'
            f'<a class="account-setup-link" href="?account_setup={account_device}" target="_self">'
            'アカウントの設定方法</a></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f'<div class="action-box"><b>{task_html}</b></div>', unsafe_allow_html=True)
    render_joint_ai_assistant(
        st.session_state.workflow_key,
        workflow,
        step,
        active,
        i,
        len(steps),
    )

    checks = []
    suffix = st.session_state.step_branches.get(step["id"], "default")
    if branch_selected:
        operation_groups = active.get("operation_groups", [])
        operations = active.get("operation_steps", [])
        check_items = active.get("checks", [])
        if operation_groups:
            operation_number = 0
            for group_index, group in enumerate(operation_groups, 1):
                st.markdown(f"#### {group.get('title', f'操作 {group_index}')}")
                st.markdown("※すべての項目にチェックを入れると次へ進めます。")
                with st.container(border=True):
                    for text in group.get("steps", []):
                        operation_number += 1
                        checks.append(
                            guide_checkbox(
                                f"{operation_number}. {text}",
                                value=bool(st.session_state.completed.get(step["id"])),
                                key=f'{step["id"]}_{suffix}_op_{operation_number}',
                            )
                        )
        elif operations:
            st.markdown("#### 操作を順番に確認")
            st.markdown("※すべての項目にチェックを入れると次へ進めます。")
            with st.container(border=True):
                for n, text in enumerate(operations, 1):
                    checks.append(
                        guide_checkbox(
                            f"{n}. {text}",
                            value=bool(st.session_state.completed.get(step["id"])),
                            key=f'{step["id"]}_{suffix}_op_{n}',
                        )
                    )
        if check_items and (not operation_groups and not operations or active.get("show_checks_after_operations")):
            st.markdown("#### 次へ進む前の確認")
            st.markdown("※すべての項目にチェックを入れると次へ進めます。")
            help_map = active.get("check_help", step.get("check_help", {}))
            with st.container(border=True):
                for n, text in enumerate(check_items, 1):
                    checkbox_key = f'{step["id"]}_{suffix}_check_{n}'
                    checks.append(
                        guide_checkbox(
                            text,
                            value=bool(st.session_state.completed.get(step["id"])),
                            key=checkbox_key,
                        )
                    )
                    if text == "SampleとOilを準備した":
                        st.markdown(oil_mixing_note_html(), unsafe_allow_html=True)
                    if text in help_map:
                        help_html = product_hover_text_html(help_map[text]).replace("\n", "<br>")
                        st.markdown(
                            f'<div class="help-box">{help_html}</div>',
                            unsafe_allow_html=True,
                        )
        if not operation_groups and not operations and not check_items:
            checks = [True]
    else:
        checks = [False]

    if active.get("notice"):
        st.warning(active["notice"])

    if active.get("user_note"):
        st.markdown("#### 利用者メモ（任意）")
        note_key = f'note_{step["id"]}'
        if note_key not in st.session_state:
            st.session_state[note_key] = st.session_state.notes.get(step["id"], "")
        note = st.text_area(
            "保存内容や出力形式などを記録してください。",
            key=note_key,
        )
        if note.strip():
            st.session_state.notes[step["id"]] = note.strip()
        else:
            st.session_state.notes.pop(step["id"], None)

    if not all(checks):
        st.session_state.completed.pop(step["id"], None)

    render_supplemental_information(active)

    if active.get("show_screen_section", True):
        st.markdown('<div class="section-title">実画面</div>', unsafe_allow_html=True)
        images = collect_screen_images(active)
        if images:
            cols = st.columns(min(2, len(images)))
            for idx, img in enumerate(images):
                with cols[idx % len(cols)]:
                    image_placeholder(
                        img["filename"],
                        img.get("title", "実画面"),
                        caption=img.get("caption", ""),
                        show_title=not img.get("hide_title", False),
                    )
        else:
            image_placeholder(f'{step["id"]}.png', step["title"])

    if active.get("show_result_sections", True):
        ok_state = active.get("ok_state") or active.get("normal_state") or []
        if "ng_state" in active:
            ng_state = active.get("ng_state") or []
        else:
            ng_state = [active.get("warning", "異常がないことを確認してください。")]

        show_ok_ng(
            ok_state,
            ng_state,
            active,
            active.get("ok_images"),
            active.get("ng_images"),
        )

    st.divider()
    prev_col, next_col = st.columns(2)
    with prev_col:
        if st.button("← 前へ", disabled=i == 0, use_container_width=True):
            st.session_state.step_index -= 1
            request_scroll_to_top()
            st.rerun()
    with next_col:
        label = "完了画面へ →" if i == len(steps) - 1 else "この工程を完了して次へ →"
        if st.button(label, type="primary", disabled=not all(checks), use_container_width=True):
            st.session_state.completed[step["id"]] = True
            save_observation(step["id"], "completed")
            st.session_state.completed[step["id"]] = True
            if i == len(steps) - 1:
                st.session_state.page = "complete"
            else:
                st.session_state.step_index += 1
            request_scroll_to_top()
            st.rerun()


def render_trouble() -> None:
    st.title("トラブルを解決する")
    troubles = DATA.get("troubleshooting", [])
    selected_symptom = str(st.session_state.get("trouble_symptom", ""))
    selected_item = next(
        (item for item in troubles if item.get("symptom") == selected_symptom),
        {},
    )
    render_page_joint_ai_assistant(
        scope="trouble",
        context={
            "page": "trouble",
            "selected_symptom": selected_symptom,
            "cause": selected_item.get("cause", ""),
            "action": selected_item.get("action", ""),
            "support_only": bool(selected_item.get("support_only")),
            "support_title": selected_item.get("support_title", ""),
        },
        prompts=[
            "この症状の原因を整理して",
            "確認手順を説明して",
            "保守へ連絡する目安は？",
        ],
        placeholder="選択中の症状や表示されている対処内容について質問してください。",
    )
    st.write("発生している症状を選ぶと、考えられる原因と確認手順を表示します。")
    if not troubles:
        st.info("症状別の案内は準備中です。")
        st.warning(DATA["contact"])
        return

    options = {item["symptom"]: item for item in troubles}
    values = [""] + list(options)
    selected = st.selectbox(
        "症状を選択してください",
        values,
        format_func=lambda value: "選択してください" if not value else value,
        key="trouble_symptom",
    )
    if selected:
        item = options[selected]
        st.markdown(f"## {item['symptom']}")
        if item.get("support_only"):
            support_title = item.get("support_title", item["symptom"])
            st.markdown("### 確認・対応")
            st.markdown(
                f'<div class="action-box">{html.escape(support_title)}の確認手順と対処方法は、'
                '株式会社オンチップ・バイオテクノロジーズの「サポート ＞ トラブルシューティング」をご覧ください。</div>',
                unsafe_allow_html=True,
            )
            st.link_button(
                "株式会社オンチップ・バイオテクノロジーズのサポートを見る",
                item.get("support_url", "https://on-chip.co.jp/support/troubleshooting/"),
                use_container_width=True,
            )
            st.caption("公式サイトの製品別トラブルシューティングが開きます。")
            st.markdown("### 改善しない場合")
            st.warning(DATA["contact"])
        else:
            st.markdown("### 考えられる原因")
            st.info(item.get("cause", "原因を確認中です。"))
            st.markdown("### 確認・対応")
            st.markdown(f'<div class="action-box">{html_lines(item.get("action", ""))}</div>', unsafe_allow_html=True)
            st.markdown("### 改善しない場合")
            st.warning(DATA["contact"])
    else:
        st.caption("症状が一覧にない場合や判断できない場合は、装置を安全に停止して保守へ連絡してください。")
        st.warning(DATA["contact"])


def render_manual_figure(filename: str, caption: str, manual_page: str, pdf_page: int) -> None:
    path = IMAGE_DIR / filename
    if path.is_file():
        st.image(str(path), use_container_width=True)
    else:
        image_placeholder(filename, caption)
    st.markdown(
        f'<div class="result-source">{html.escape(caption)}</div>',
        unsafe_allow_html=True,
    )


def render_custom_figure(filename: str, caption: str) -> None:
    path = IMAGE_DIR / filename
    if path.is_file():
        st.image(str(path), use_container_width=True)
    else:
        image_placeholder(filename, caption)
    st.markdown(
        f'<div class="result-source">{html.escape(caption)}</div>',
        unsafe_allow_html=True,
    )


RESULT_PAGES = [
    {"key": "step1", "label": "STEP 1", "short": "信号と軸を知る"},
    {"key": "step2", "label": "STEP 2", "short": "蛍光と検出を知る"},
    {"key": "step3", "label": "STEP 3", "short": "プロットを選ぶ"},
    {"key": "step4", "label": "STEP 4", "short": "ゲートを作る"},
    {"key": "step5", "label": "STEP 5", "short": "集団を展開する"},
    {"key": "step6", "label": "STEP 6", "short": "感度・閾値・表示倍率"},
    {"key": "step7", "label": "STEP 7", "short": "蛍光補正"},
    {"key": "step8", "label": "STEP 8", "short": "階層・ソート・分注"},
]


def render_results_header() -> None:
    st.title("測定結果を確認する")
    st.markdown(
        """
        <div class="results-hero">
            <div class="results-hero-title">測定結果を読み解くためのプロット解説</div>
            <div>信号の見方から、プロット、ゲートによる集団の選択、ソーティング・分注までを、具体例を交えながら順番に説明します。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "本文の中心は添付マニュアルです。紫色の「一般的なFACSの補足」は、マニュアル記載事項と区別して表示しています。"
    )


def render_results_ai() -> None:
    st.divider()
    st.markdown("## JointAIによるプロット見解（準備中）")
    st.markdown(
        """
        <div class="results-ai">
        将来は、この解説を確認した後にプロットデータをドラッグ＆ドロップし、軸、分布、ゲート、測定条件、注意点についてAIの見解を表示する予定です。対応するプログラムデータと入力形式が確定してから実装します。現在はデータのアップロードやAI解析は行いません。
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button("プロットデータをアップロード（準備中）", disabled=True, use_container_width=True, key="results_ai_pending")


def render_results_index() -> None:
    render_page_joint_ai_assistant(
        scope="results_index",
        context={
            "page": "results",
            "overview": "測定結果を読み解くためのプロット解説",
            "topics": [item["short"] for item in RESULT_PAGES],
        },
        prompts=[
            "どの項目から確認すればよい？",
            "プロットの見方を教えて",
            "ゲート設定の注意点は？",
        ],
        placeholder="測定結果の見方や確認項目について質問してください。",
    )
    st.markdown("## 確認する項目を選択してください")
    st.markdown(
        '<div class="results-page-context">各項目は単独ページで表示されます。前後の項目へ移動するか、一覧へ戻って選び直せます。</div>',
        unsafe_allow_html=True,
    )
    for row_start in (0, 4):
        columns = st.columns(4, gap="small")
        for column, item in zip(columns, RESULT_PAGES[row_start:row_start + 4]):
            with column:
                if st.button(
                    f"{item['label']}\n{item['short']}",
                    use_container_width=True,
                    key=f"results_open_{item['key']}",
                ):
                    open_results(item["key"])
    render_results_ai()


def render_result_navigation(current_key: str) -> None:
    current_index = next(i for i, item in enumerate(RESULT_PAGES) if item["key"] == current_key)
    previous_item = RESULT_PAGES[current_index - 1] if current_index > 0 else None
    next_item = RESULT_PAGES[current_index + 1] if current_index < len(RESULT_PAGES) - 1 else None

    st.divider()
    previous_col, index_col, next_col = st.columns([1, 1, 1])
    with previous_col:
        previous_label = (
            f"← {previous_item['label']}　{previous_item['short']}"
            if previous_item
            else "← 前の項目"
        )
        if st.button(
            previous_label,
            disabled=previous_item is None,
            use_container_width=True,
            key=f"results_nav_prev_{current_key}",
        ):
            open_results(previous_item["key"])
    with index_col:
        if st.button(
            "項目一覧へ戻る",
            use_container_width=True,
            key=f"results_nav_index_{current_key}",
        ):
            open_results()
    with next_col:
        next_label = (
            f"{next_item['label']}　{next_item['short']} →"
            if next_item
            else "次の項目 →"
        )
        if st.button(
            next_label,
            disabled=next_item is None,
            use_container_width=True,
            key=f"results_nav_next_{current_key}",
        ):
            open_results(next_item["key"])


def render_result_step1() -> None:
    st.markdown('<div class="result-step-title">STEP 1　最初に、信号と軸の意味を確認する</div>', unsafe_allow_html=True)
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        render_manual_figure(
            "selector_optics_fsc_ssc.png",
            "チップ内でのレーザー照射とFSC・SSC・蛍光の検出方向",
            "1-4-3 チップ内光学系（1-9）",
            20,
        )
    with right:
        st.markdown(
            """
            <div class="result-card"><b>装置は、対象から返ってくる光を分けて測ります</b><br>
            細胞、粒子、ドロップレットなどへレーザー光を当てると、光は前や横へ散り、蛍光色素などを使っている場合は別の色の光も出ます。装置は、それぞれの光を別の検出器で受け取り、グラフにできる数値へ変えます。<br><br>
            <b>FSC</b>はレーザーの進行方向に近い側で測る前方散乱光です。細胞や粒子の大きさを考える手がかりになります。<b>SSC</b>は横方向で測る側方散乱光で、内部の粒状性や複雑さを考える手がかりになります。ただし、FSCやSSCだけで液滴の直径や封入された細胞数を決めることはできません。<br><br>
            <b>FL1〜FL6</b>は蛍光を色や波長の範囲ごとに受け取る6つの検出チャンネルです。数字が大きいほど蛍光が強いという意味ではなく、どの色の光を受け取る場所かを区別する番号です。グラフを見るときは、最初に縦軸と横軸の信号名を確認してください。</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="result-key"><b>パルスと軸名の読み方</b><br>
        細胞、粒子、ドロップレットなどがレーザーを通過すると、検出器には一時的な信号の波形である<b>パルス</b>が生じます。1つのパルスは、高さ、幅、面積の3つの見方で数値化できます。<br><br>
        H = Height（パルスの高さ）、W = Width（パルス幅）、A = Area（パルス面積）です。同じFSCでもFSC-H、FSC-W、FSC-Aは別の量として扱います。</div>
        <div class="result-caution"><b>ドロップレット解析での重要な注意</b><br>
        FSCやSSCの値を、そのまま液滴の大きさ、内部の複雑さ、封入された細胞数に置き換えて判断しないでください。散乱光は液滴径だけでなく、油相と水相の界面、液滴の形、流路を通る位置、測定条件などの影響を受けることがあります。<br><br>
        例えば、FSCとSSCが高い位置に集団が見えても、それだけで「大きい液滴」や「細胞を多く含む液滴」とは断定できません。FSC・SSCは、ドロップレットらしいイベントの範囲や明らかな外れを探すための補助情報として使い、目的蛍光、対照試料、必要に応じて画像や顕微鏡観察と組み合わせて確認します。</div>
        <div class="result-general"><b>イベントとは</b><br>
        プロット上の1点は、装置が1回検出した「イベント」です。目的のドロップレットとは限らず、微細な粒子、複数イベントの同時通過などを含むことがあります。点の位置だけで内容物を決めず、後のゲートと蛍光信号で絞り込みます。</div>
        """,
        unsafe_allow_html=True,
    )


def render_result_step2() -> None:
    st.markdown('<div class="result-step-title">STEP 2　蛍光と検出チャンネルを理解する</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="result-card"><b>蛍光測定の基本</b><br>
        蛍光測定では、細胞や粒子にレーザー光を当て、蛍光色素や蛍光タンパク質から返ってくる光を測ります。色素ごとに、光りやすいレーザーの波長と、発する光の色が異なります。装置はその光をフィルターで分け、FL1〜FL6の検出チャンネルへ振り分けて記録します。<br><br>
        <b>励起光</b>は色素を光らせるために当てる光、<b>蛍光</b>は色素がその後に出す別の波長の光です。同じレーザーで光らせる色素でも、発する色が違えば主に見るFLチャンネルが異なります。また、1つの色素の光が複数のチャンネルへ少し入ることもあります。</div>
        """,
        unsafe_allow_html=True,
    )
    render_fluorescence_wavelength_figure()
    st.markdown(
        """
        <div class="fluor-system-grid">
          <div><strong>励起レーザー</strong><span style="color:#7b2cbf;">●</span> 405 nm、<span style="color:#1677d2;">●</span> 488 nm、<span style="color:#168a3a;">●</span> 561 nm、<span style="color:#d62828;">●</span> 637 nm</div>
          <div><strong>蛍光検出</strong>FL1〜FL6の6チャンネル</div>
          <div><strong>散乱光</strong>FSCとSSC。蛍光色素から出る光ではありません。</div>
        </div>
        <div class="result-key"><b>色素とチャンネルの見方</b><br>
        下の表は、各色素や蛍光タンパク質を確認するときに使う励起レーザーと、主な検出チャンネルの目安です。実際の見え方は、色素の蛍光特性、装置のフィルター、試料条件、他の色からの漏れ込みによって変わります。複数色を同時に使う場合は、単染色対照と蛍光補正も確認してください。<br><br>
        <b>On-chip Droplet SelectorとOn-chip Sortは同じ検出系です。</b>どちらも、使用する蛍光物質の励起特性と検出チャンネルの組み合わせを確認して測定条件を決めます。</div>
        """,
        unsafe_allow_html=True,
    )

    fnap_6fam = product_hover_span_html(
        "FNAP-sort (6-FAM)",
        "On-chip FNAP-sort (6-FAM)",
    )
    mime_green = product_hover_span_html(
        "MiMe-Stain Green",
        "On-chip MiMe-Stain Green",
    )
    mime_red = product_hover_span_html(
        "MiMe-Stain Red",
        "On-chip MiMe-Stain Red",
    )
    fnap_cy5 = product_hover_span_html(
        "FNAP-sort (Cy5)",
        "On-chip FNAP-sort (Cy5)",
    )
    st.markdown(
        f"""
        <h3>代表的な蛍光色素・蛍光タンパク質</h3>
        <div class="fluor-table-wrap">
        <table class="fluor-table">
          <thead>
            <tr><th>励起光の区分</th><th>FL1</th><th>FL2</th><th>FL3</th><th>FL4</th><th>FL5</th><th>FL6</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>Violet</td>
              <td>DAPI、AF405、Pacific Blue、V450、BV421、Hoechst 33342、Calcofluor White</td>
              <td>Pacific Orange、V500、BV510</td>
              <td>Pacific Orange、BV605</td>
              <td class="fluor-empty">―</td>
              <td>BV650</td>
              <td>BV711、BV786</td>
            </tr>
            <tr>
              <td>Blue</td>
              <td class="fluor-empty">―</td>
              <td>FITC、AF488、GFP、CFP、YFP、SYTO 9、SYTOX Green、Calcein AM、FUN-1、{fnap_6fam}、YOYO-1</td>
              <td>PE、FUN-1、CTC、{mime_green}</td>
              <td>PI、7-AAD</td>
              <td>PerCP、PerCP-Cy5.5、PE-Cy5</td>
              <td>PE-Cy7、{mime_red}</td>
            </tr>
            <tr>
              <td>Green</td>
              <td class="fluor-empty">―</td>
              <td class="fluor-empty">―</td>
              <td>DsRed、mCherry、tdTomato、TagRFP、SYTOX Orange、TMRM／TMRE</td>
              <td class="fluor-empty">―</td>
              <td class="fluor-empty">―</td>
              <td class="fluor-empty">―</td>
            </tr>
            <tr>
              <td>Red</td>
              <td class="fluor-empty">―</td>
              <td class="fluor-empty">―</td>
              <td class="fluor-empty">―</td>
              <td class="fluor-empty">―</td>
              <td>APC、AF647、SYTOX Red、DRAQ5、DRAQ7、{fnap_cy5}</td>
              <td>APC-Cy7、APC-H7、AF700</td>
            </tr>
          </tbody>
        </table>
        </div>
        <div class="result-caution"><b>一覧の使い方</b><br>
        これは検出系資料と各色素の代表的な特性を基にした目安です。実際の検出可否や最適なチャンネルは、蛍光物質の励起・蛍光スペクトル、フィルター構成、試料、測定条件によって変わります。使用前に装置仕様書と試薬メーカーの情報を確認してください。複数色を同時測定する場合は、チャンネル間の漏れ込みと蛍光補正も確認します。青い点線付きの製品名は、カーソルまたはキーボードのフォーカスで製品一覧の情報を確認できます。</div>
        """,
        unsafe_allow_html=True,
    )


def render_result_step3() -> None:
    st.markdown('<div class="result-step-title">STEP 3　プロットの種類と軸スケールを選ぶ</div>', unsafe_allow_html=True)
    st.markdown(
        "前項で検出・記録された各イベントの測定値は、分布や項目同士の関係を確認しやすくするため、グラフ（プロット）として表示します。ここでは、確認したい内容に合わせて、プロットの種類と軸スケールを選択します。"
    )

    with st.container(border=True):
        st.markdown('<div class="result-explainer-marker"></div>', unsafe_allow_html=True)
        copy_col, figure_col = st.columns([1, 1.45], gap="large")
        with copy_col:
            st.markdown(
                """
                <div class="result-explainer-copy">
                  <h3>ドットプロット</h3>
                  <p>1点が1イベントです。横軸と縦軸の2つの測定値を同時に比べます。右へ行くほど横軸の値が強く、上へ行くほど縦軸の値が強くなります。</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with figure_col:
            render_custom_figure(
                "selector_dot_plot_explained.png",
                "ドットプロット：1点が1イベント。横軸と縦軸の2つの信号を同時に比較する",
            )

    with st.container(border=True):
        st.markdown('<div class="result-explainer-marker"></div>', unsafe_allow_html=True)
        copy_col, figure_col = st.columns([1, 1.45], gap="large")
        with copy_col:
            st.markdown(
                """
                <div class="result-explainer-copy">
                  <h3>デンシティープロット</h3>
                  <p>ドットプロットと同じデータを、イベントが多い場所ほど濃い色で表示します。点が重なって見えにくい場合でも、集団が集中している場所を確認しやすくなります。</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with figure_col:
            render_custom_figure(
                "selector_density_plot_explained.png",
                "デンシティープロット：色が濃い場所ほどイベントが多く集まっている",
            )

    with st.container(border=True):
        st.markdown('<div class="result-explainer-marker"></div>', unsafe_allow_html=True)
        copy_col, figure_col = st.columns([1, 1.45], gap="large")
        with copy_col:
            st.markdown(
                """
                <div class="result-explainer-copy">
                  <h3>ヒストグラム</h3>
                  <p>1つの測定値の分布を表示します。横軸は測定値の強さ、縦方向はイベント数です。山が右にあるほど測定値が強く、山が高いほどその強度のイベントが多いことを示します。</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with figure_col:
            render_custom_figure(
                "selector_histogram_explained.png",
                "ヒストグラム：右ほど測定値が強く、山が高いほどその強度のイベントが多い",
            )

    st.markdown(
        """
        <div class="result-key"><b>読む順番</b><br>
        ①軸が何を表すか → ②スケールは何か → ③点や山がどこにあるか、の順に確認します。グラフの形だけを先に見ないことが重要です。</div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("マニュアル画面でプロット形式と軸スケールを確認する"):
        c1, c2 = st.columns([1.55, 1], gap="large")
        with c1:
            render_manual_figure(
                "selector_plot_types.png",
                "デンシティープロット、単色ドットプロット、カラードットプロットの表示例",
                "2-4-1 パネルの表示（2-21）",
                48,
            )
        with c2:
            render_manual_figure(
                "selector_axis_scale.png",
                "軸パラメーターとLinear・Logarithmic・Bi Exponentialの選択画面",
                "2-4-1 パネルの表示（2-21）",
                48,
            )
    st.markdown(
        """
        <div class="result-key"><b>選択できるスケール</b><br>
        軸はLinear、Logarithmic、Bi Exponentialから選択できます。LogarithmicとBi Exponentialでは、表示する最小値を10、1、0.1から選択できます。</div>
        <div class="result-general"><b>一般的なFACSの補足</b><br>
        Linearは差を等間隔で、Logarithmicは広い強度範囲を圧縮して表示します。Bi Exponentialは低い値や補正後に0付近へ広がる分布を確認するときに使われます。異なるスケールの図を、同じ見え方として直接比較しないでください。</div>
        """,
        unsafe_allow_html=True,
    )

def render_result_step4() -> None:
    st.markdown('<div class="result-step-title">STEP 4　ゲートを作り、見たい集団を定義する</div>', unsafe_allow_html=True)
    copy_col, figure_col = st.columns([1, 1.2], gap="large")
    with copy_col:
        st.markdown(
            """
            <div class="result-card"><b>ゲートとは</b><br>
            プロット上の点は、それぞれ1つの細胞やドロップレットなど、装置が検出した1回分の測定結果を表します。ゲートは、その点の中から解析したいイベントだけを選ぶための囲みです。四角形や多角形などで範囲を囲むと、その中に入ったイベントだけを選択できます。選択されたイベントの集まりを<b>ポピュレーション</b>と呼びます。<br><br>
            <b>たとえば</b><br>
            色や大きさの異なるボールが箱に入っていて、「大きい青色のボールだけ」を選ぶ場面を考えます。箱の中のすべてのボールが全イベント、「大きくて青い」という選択範囲がゲート、条件に合って選ばれたボールの集まりがポピュレーションに相当します。</div>
            """,
            unsafe_allow_html=True,
        )
    with figure_col:
        render_custom_figure(
            "selector_gate_basic.png",
            "説明イメージ：プロット上のゲートと、ゲート内に選ばれたポピュレーション",
        )
    st.markdown(
        """
        <div class="result-compare">
          <div><strong>ボックスゲート</strong>四角形の内側にあるイベントを選びます。</div>
          <div><strong>クロスゲート</strong>縦線と横線でプロットを4つの領域に分けます。</div>
          <div><strong>ポリゴンゲート</strong>複数の点を結び、任意の形でイベントを囲みます。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_custom_figure(
        "selector_histogram_gates.png",
        "ヒストグラムのゲート：サンドイッチは2本の線の間を選び、スプリッターは1本の線で左右に分ける",
    )
    st.markdown(
        """
        <div class="result-key"><b>名称より先に動きを確認</b><br>
        <b>サンドイッチゲート</b>は、下限と上限を決めて、その間にあるイベントだけを選びます。<br>
        <b>スプリッターゲート</b>は、1つの境界値を決めて、低い側と高い側の2群に分けます。陰性群と陽性群を分ける場合などに使用します。</div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("マニュアル画面でゲートツールと操作例を確認する"):
        c1, c2 = st.columns([1.1, 1.1], gap="large")
        with c1:
            render_manual_figure(
                "selector_gate_tools.png",
                "ドット／デンシティープロット用とヒストグラム用のゲートツール",
                "2-4-2 ツールバー（2-23）",
                50,
            )
        with c2:
            render_manual_figure(
                "selector_gate_dragdrop.png",
                "ゲートしたポピュレーションを別パネルへドラッグ＆ドロップする例",
                "2-4-2 ツールバー（2-23）",
                50,
            )
    st.markdown(
        """
        <div class="result-general"><b>ゲート名と読み方の例</b><br>
        ゲートは自動的な正解ではなく、解析者が設定した選別条件です。P1、P2だけでなく「散乱光上の主要集団」「ドロップレット候補」「FL2陽性候補」のように、何を選んだか分かる名前を付けると階層を追いやすくなります。<br><br>
        ドロップレット解析では、FSC・SSCで囲んだ集団を内容物が確定した集団とは考えず、次の蛍光解析へ進むための仮の絞り込みとして扱います。対照試料と比較し、境界付近のイベントを含めるかどうかを確認します。</div>
        """,
        unsafe_allow_html=True,
    )


def render_result_step5() -> None:
    st.markdown('<div class="result-step-title">STEP 5　選んだ集団を別の軸へ展開する</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.15], gap="large")
    with c1:
        st.markdown(
            """
            <div class="result-card">
            最初のプロットで作ったポピュレーションを選び、別パネルでFSC、SSC、蛍光の組み合わせを表示します。画像では、FSC-SSCで選んだP1を、FL2-B(H)とFSC(H)のプロットへ展開しています。<br><br>
            ドロップレットでは、空液滴と封入液滴がFSC・SSC上で重なることがあります。そのため、散乱光で候補を絞った後に目的蛍光へ展開し、空ドロップレット、未染色試料、陽性対照との違いを確認します。展開後の点は全イベントではなく、親ゲートを通過したイベントだけです。
            </div>
            <div class="result-key"><b>例を使った読み進め方</b><br>
            ①FSC・SSCで大まかな主要集団を囲む → ②その親集団を確認する → ③目的蛍光を軸にしたプロットへ展開する → ④空ドロップレットや未染色対照と比べる → ⑤必要なら蛍光陽性候補のゲートを作る、の順番です。</div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        render_manual_figure(
            "selector_gate_expansion.png",
            "P1ポピュレーションを別の軸へ展開するStep 1・Step 2",
            "4-13-3 ゲートの展開（4-25）",
            108,
        )


def render_result_step6() -> None:
    st.markdown('<div class="result-step-title">STEP 6　Gain、Threshold、Numerical Factorを区別する</div>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="result-explainer-marker"></div>', unsafe_allow_html=True)
        copy_col, figure_col = st.columns([1, 1.45], gap="large")
        with copy_col:
            st.markdown(
                """
                <div class="result-explainer-copy">
                  <h3>Gain（検出感度）</h3>
                  <p>検出器が信号をどの程度強く受け取るかを調整します。弱すぎると分布が左端、強すぎると右端へ張り付くことがあります。</p>
                  <div class="result-explainer-note">測定途中で変更した場合は、一旦停止して再測定します。</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with figure_col:
            render_custom_figure(
                "selector_gain_clear.png",
                "Gain調整の目安：分布が表示範囲の端へ張り付かず、全体が見える状態を確認する",
            )

    with st.container(border=True):
        st.markdown('<div class="result-explainer-marker"></div>', unsafe_allow_html=True)
        copy_col, figure_col = st.columns([1, 1.45], gap="large")
        with copy_col:
            st.markdown(
                """
                <div class="result-explainer-copy">
                  <h3>Threshold（記録する最低ライン）</h3>
                  <p>どの強さ以上の信号をイベントとして記録するかを決めます。低すぎると不要な微細イベントを拾い、高すぎると目的イベントを落とす可能性があります。</p>
                  <div class="result-explainer-note">複数条件を使う場合は、AND／ORと各Parameter・Valueの組み合わせも確認します。</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with figure_col:
            render_manual_figure(
                "selector_threshold_only.png",
                "Threshold欄：AND／OR、Parameter、Valueを設定する",
                "4-13-5 Thresholdの設定（4-27）",
                110,
            )

    with st.container(border=True):
        st.markdown('<div class="result-explainer-marker"></div>', unsafe_allow_html=True)
        copy_col, figure_col = st.columns([1, 1.45], gap="large")
        with copy_col:
            st.markdown(
                """
                <div class="result-explainer-copy">
                  <h3>Numerical Factor（表示倍率）</h3>
                  <p>測定後の数値に倍率を掛け、グラフ上の表示位置だけを動かします。例えば2.0にすると、プロットは値が2倍の位置に表示されます。分布がグラフの端に寄っている場合は、イベントが集中している部分を見やすい位置へ移動できます。</p>
                  <div class="result-explainer-note"><b>検出器が受け取る信号や感度は変わりません。</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with figure_col:
            render_custom_figure(
                "selector_numerical_factor.png",
                "Numerical Factor 1.0と2.0：同じ測定データの表示位置だけが2倍になり、分布の形や検出信号は変わらない",
            )

    with st.expander("Gain・Numerical Factor・Thresholdの設定画面全体を確認する"):
        render_manual_figure(
            "selector_threshold_settings.png",
            "Gain、Numerical Factor、Thresholdの設定画面",
            "4-13-5 Thresholdの設定（4-27）",
            110,
        )

    st.markdown(
        """
        <div class="result-caution"><b>ドロップレット解析でのThresholdの注意</b><br>
        FSCのThresholdだけで目的ドロップレットを定義しないでください。低すぎると不要な微細イベントを多く拾い、高すぎると目的のドロップレットを除外する可能性があります。空ドロップレット、未染色対照、目的蛍光、陽性対照の分布を見ながら、測定目的に応じて設定します。<br><br>
        また、プロットが中央に収まっているだけでは良い測定とは判断できません。比較する試料間でGain、Threshold、Numerical Factorなどの条件がそろっているかを確認します。</div>
        """,
        unsafe_allow_html=True,
    )

def render_result_step7() -> None:
    st.markdown('<div class="result-step-title">STEP 7　蛍光補正（Compensation）を理解する</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1.1, 1], gap="large")
    with c1:
        render_manual_figure(
            "selector_compensation.png",
            "蛍光スペクトルの漏れ込みと、補正前・補正後の分布イメージ",
            "4-13-7 Compensation（蛍光補正）（4-29）",
            112,
        )
    with c2:
        st.markdown(
            """
            <div class="result-card">
            2色以上を同時に測定すると、ある蛍光色の信号が別の検出チャンネルにも入り込むことがあります。Compensationは、単染色コントロールから漏れ込み率を求め、各チャンネルの信号を補正して蛍光強度を推定し直す処理です。<br><br>
            緑の信号がFL3へ、赤の信号がFL2へ漏れ込む場合などに、補正後の単染色集団が軸に沿う状態を目安として確認します。
            </div>
            <div class="result-key"><b>蛍光補正が反映されるとき</b><br>
            蛍光補正は、測定を始めただけで自動的に「発動」するものではありません。未染色コントロールと各蛍光色の単染色コントロールを用意し、漏れ込み率を計算または設定したうえで、補正をONにする、または対象ファイルへ補正条件を適用したときに反映されます。装置や解析ソフトによって、補正値の計算方法は自動または手動です。</div>
            <div class="result-key"><b>確認するもの</b><br>
            単染色コントロール、未染色コントロール、補正のON/OFF、補正を適用したファイルかどうかを確認します。補正後に保存する場合は、Save操作も確認します。</div>
            <div class="result-general"><b>一般的なFACSの補足</b><br>
            主な対象は、発光スペクトルが重なる複数色測定です。単色測定や、検出器間の漏れ込みが無視できる条件では原則として不要です。補正は蛍光の重なりを分離する処理であり、非特異染色や自家蛍光を消す処理ではありません。適切な単染色コントロールがない状態では正しい補正値を設定できません。補正条件が異なるファイルを、そのまま同一基準で比較しないでください。</div>
            """,
            unsafe_allow_html=True,
        )

def render_result_step8() -> None:
    st.markdown('<div class="result-step-title">STEP 8　ゲート階層を読み、ソーティング・分注へつなげる</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="result-card"><b>用語を先に整理</b><br>
        <b>ゲート</b>＝イベントを選ぶ条件、<b>ポピュレーション</b>＝その条件に入ったイベントの集まりです。ゲートを重ねると、どの条件を通って現在の集団になったかが階層として表示されます。</div>
        """,
        unsafe_allow_html=True,
    )
    render_custom_figure(
        "selector_gate_logic.png",
        "AND条件は親の中をさらに絞り、OR条件はGroup AまたはGroup Bのどちらかに入るイベントを対象にする",
    )
    st.markdown(
        """
        <div class="result-compare">
          <div><strong>親ゲートと子ゲート：AND条件</strong>まず親ゲートで対象を絞り、その中に子ゲートを作ります。子ポピュレーションに含まれるのは、<b>親ゲートを通過し、さらに子ゲートの条件も満たしたイベント</b>だけです。<br><br>例：散乱光で候補を選ぶ → その中から蛍光が強いイベントを選ぶ。</div>
          <div><strong>Group AとGroup B：OR条件</strong>Group AとGroup Bを独立して作り、それぞれにソーティングゲートを設定すると、<b>Group AまたはGroup Bのどちらかに入るイベント</b>を選別対象にできます。</div>
          <div><strong>階層を読むときの確認</strong>現在表示している点が「全イベント」なのか、「親ゲートを通過したイベントだけ」なのかを確認します。ゲート名は、選んだ対象が分かる名前にすると追いやすくなります。</div>
        </div>
        <div class="result-caution"><b>ソーティング時の階層制限</b><br>
        マニュアルでは、ソーティングに使用するゲートは10階層までとされています。解析だけに使うゲートには、この階層制限はありません。</div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("マニュアル画面でゲート階層とORゲートの設定例を確認する"):
        c1, c2 = st.columns(2, gap="large")
        with c1:
            render_manual_figure(
                "selector_gate_hierarchy.png",
                "複数プロットとPopulation Managementに表示されたゲート階層",
                "4-13-8 ゲート階層の表示（4-40）",
                123,
            )
        with c2:
            render_manual_figure(
                "selector_or_gate.png",
                "Groupe-AとGroupe-Bを用いた2つのソーティングゲートの設定例",
                "4-13-8 ゲート階層の表示（4-41）",
                124,
            )
    st.markdown("### ソーティング・分注へつなげる")
    c1, c2 = st.columns([1.05, .9], gap="large")
    with c1:
        render_manual_figure(
            "selector_dispense_population.png",
            "Work spaceまたはPopulation spaceから分注対象を選択する画面",
            "4-13-9 Dispense（分注）（4-42）",
            125,
        )
    with c2:
        render_manual_figure(
            "selector_dispense_wells.png",
            "分注先ウェルの選択前・選択後",
            "4-13-10 分注設定（4-45）",
            128,
        )
    st.markdown(
        """
        <div class="result-key"><b>「何を」と「どこへ」を分けて確認</b><br>
        プロットとゲートは、ソーティング・分注する<b>対象ポピュレーション</b>を決めます。ウェルシートは、その対象を<b>どのウェルへ分注するか</b>を決めます。対象ゲート、Select population、DispenseのON/OFF、プレートとウェルの選択を別々に確認してください。</div>
        """,
        unsafe_allow_html=True,
    )


def render_results() -> None:
    current_key = st.session_state.get("result_step", "")
    if current_key == "check":
        current_key = "step8"
        st.session_state.result_step = current_key
    renderers = {
        "step1": render_result_step1,
        "step2": render_result_step2,
        "step3": render_result_step3,
        "step4": render_result_step4,
        "step5": render_result_step5,
        "step6": render_result_step6,
        "step7": render_result_step7,
        "step8": render_result_step8,
    }
    if current_key not in renderers:
        st.session_state.result_step = ""
        render_results_header()
        render_results_index()
        return

    st.title("測定結果を確認する")
    renderers[current_key]()
    render_result_navigation(current_key)

def render_glossary() -> None:
    st.title("用語集")
    if GLOSSARY_ERROR:
        st.error(f"用語集データを読み込めませんでした: {GLOSSARY_ERROR}")
        return

    entries = GLOSSARY.get("entries", [])
    st.markdown(
        """<div class="glossary-hero"><b>このソフトに登場する専門用語を、初めて学ぶ人向けに説明します。</b><br>
        製品名、製品番号、製品仕様は用語集に重複掲載せず、「製品一覧」で確認してください。</div>""",
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "用語・略語・説明文から検索",
        key="glossary_query",
        placeholder="例：FSC、粘度、ドロップレット、JSON",
    ).strip()
    categories = GLOSSARY.get("categories", [])
    selected_category = st.selectbox(
        "分野",
        ["すべて", *categories],
        key="glossary_category",
    )

    normalized_query = query.casefold()
    filtered = []
    for item in entries:
        if selected_category != "すべて" and item.get("category") != selected_category:
            continue
        searchable = " ".join(
            [
                str(item.get("term", "")),
                *[str(alias) for alias in item.get("aliases", [])],
                str(item.get("category", "")),
                str(item.get("description", "")),
            ]
        ).casefold()
        if normalized_query and normalized_query not in searchable:
            continue
        filtered.append(item)

    st.caption(f"表示：{len(filtered)}語 ／ 全{len(entries)}語")
    if not filtered:
        st.markdown('<div class="glossary-empty">条件に一致する用語はありません。検索語または分野を変更してください。</div>', unsafe_allow_html=True)
        return

    grouped = {category: [] for category in categories}
    for item in filtered:
        grouped.setdefault(item.get("category", "その他"), []).append(item)

    blocks = []
    for category in [*categories, *[key for key in grouped if key not in categories]]:
        category_entries = grouped.get(category, [])
        if not category_entries:
            continue
        blocks.append(f'<div class="glossary-category">{html.escape(category)}</div>')
        blocks.append('<div class="glossary-table">')
        for item in category_entries:
            aliases = [str(alias) for alias in item.get("aliases", []) if str(alias).strip()]
            alias_html = (
                f'<span class="glossary-aliases">別名・検索語：{html.escape("、".join(aliases))}</span>'
                if aliases
                else ""
            )
            blocks.append(
                '<div class="glossary-row">'
                f'<div class="glossary-term">{html.escape(str(item.get("term", "")))}{alias_html}</div>'
                f'<div class="glossary-description">{html.escape(str(item.get("description", "")))}</div>'
                '</div>'
            )
        blocks.append('</div>')
    st.markdown("".join(blocks), unsafe_allow_html=True)


def render_products() -> None:
    st.title("製品一覧")
    if PRODUCT_CATALOG_ERROR:
        st.error(f"製品一覧データを読み込めませんでした: {PRODUCT_CATALOG_ERROR}")
        return

    total = product_count(PRODUCT_CATALOG)
    source_title = "オンチップ・バイオテクノロジーズ 製品一覧"
    st.markdown(
        f'<div class="product-hero"><b>{source_title}</b><br>'
        '製品番号、製品名、用途・仕様で検索できます。</div>',
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "製品名・製品番号・仕様で検索",
        key="product_catalog_query",
        placeholder="例：1060DG、Droplet Selector、蛍光、チップ",
    )
    device_labels = {
        "すべて": "",
        "Droplet Selector": "DS",
        "On-chip Sort": "OS",
        "Droplet Generator": "DG",
        "Droplet Generator S": "DGS",
    }
    device_label = st.selectbox(
        "機種",
        list(device_labels),
        key="product_catalog_device",
    )
    group_labels = [
        group.get("label", "") for group in PRODUCT_CATALOG.get("groups", [])
    ]
    c1, c2 = st.columns(2)
    with c1:
        group_options = ["すべて", *group_labels]
        default_group = "試薬・消耗品"
        default_group_index = (
            group_options.index(default_group)
            if default_group in group_options
            else 0
        )
        group_label = st.selectbox(
            "大分類",
            group_options,
            index=default_group_index,
            key="product_catalog_group",
        )
    categories = []
    if group_label == "試薬・消耗品":
        categories = device_compatibility_categories(PRODUCT_CATALOG)
    else:
        for group in PRODUCT_CATALOG.get("groups", []):
            if group_label == "すべて" or group.get("label") == group_label:
                categories.extend(
                    category.get("label", "")
                    for category in group.get("categories", [])
                )
    with c2:
        category_label = st.selectbox(
            "カテゴリー",
            ["すべて", *categories],
            key="product_catalog_category",
        )

    products = filter_products(
        PRODUCT_CATALOG,
        query=query,
        group_label=group_label,
        category_label=category_label,
        device_compatibility=device_labels[device_label],
    )
    notes = list(PRODUCT_CATALOG.get("notes", []))
    if group_label == "装置":
        notes = []
    elif group_label == "オプション":
        notes = [
            note
            for note in notes
            if "SPiS Dispensing Tip 384S" not in str(note)
        ]
    if notes:
        st.markdown("### 製品データの注記")
        for note in notes:
            st.markdown(
                f'<div class="product-note">{html.escape(str(note))}</div>',
                unsafe_allow_html=True,
            )
    st.caption(f"表示：{len(products)}件 ／ 全{total}件")
    if not products:
        st.info("条件に一致する製品はありません。検索語またはカテゴリーを変更してください。")
        return

    for start in range(0, len(products), 2):
        columns = st.columns(2, gap="medium")
        for column, product in zip(columns, products[start:start + 2]):
            attributes = "".join(
                f'<div class="product-attribute"><b>{html.escape(str(item.get("label", "")))}</b><br>'
                f'{html_lines(item.get("value", ""))}</div>'
                for item in product.get("attributes", [])
            )
            with column:
                product_number = str(product.get("product_number", ""))
                image_filename = PRODUCT_IMAGE_BY_NUMBER.get(product_number, "")
                image_uri = (
                    product_image_data_uri(str(PRODUCT_IMAGE_DIR / image_filename))
                    if image_filename
                    else ""
                )
                if image_uri:
                    product_name = " ".join(str(product.get("product_name", "")).split())
                    card_body = (
                        '<div class="product-card-body has-image">'
                        f'<div class="product-card-attributes">{attributes}</div>'
                        '<div class="product-card-image-wrap">'
                        f'<img class="product-card-image" src="{image_uri}" '
                        f'alt="{html.escape(product_name)}" loading="lazy" decoding="async">'
                        '</div></div>'
                    )
                else:
                    card_body = attributes
                st.markdown(
                    f'<div class="product-card">'
                    f'<div class="product-card-category">{html.escape(product.get("group", ""))}｜'
                    f'{html.escape(product.get("category", ""))}</div>'
                    f'<div class="product-card-title">{html_lines(product.get("product_name", ""))}</div>'
                    f'<div class="product-card-number">製品番号：'
                    f'{html.escape(product_number)}</div>'
                    f'{card_body}</div>',
                    unsafe_allow_html=True,
                )


def _save_experiment_condition_report(record_id: str, uploaded_file) -> tuple[dict, Path]:
    payload = uploaded_file.getvalue()
    if not payload:
        raise ValueError("添付するカルテの内容を読み込めませんでした。")

    safe_name = Path(str(uploaded_file.name)).name or "experiment_condition_report.pdf"
    record_dir = EXPERIMENT_RECORD_ATTACHMENTS_DIR / record_id
    record_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    target = record_dir / f"condition_report_{stamp}.pdf"
    temp_target = target.with_suffix(target.suffix + ".tmp")
    try:
        temp_target.write_bytes(payload)
        temp_target.replace(target)
    except OSError as exc:
        try:
            temp_target.unlink(missing_ok=True)
        except OSError:
            pass
        raise ValueError(f"実験条件検討カルテを保存できませんでした: {exc}") from exc

    metadata = {
        "name": safe_name,
        "size": len(payload),
        "stored_path": target.relative_to(BASE_DIR).as_posix(),
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    return metadata, target


def _remove_experiment_condition_report_file(metadata: dict | None) -> None:
    if not isinstance(metadata, dict):
        return
    stored_path = str(metadata.get("stored_path", "")).strip()
    if not stored_path:
        return
    candidate = (BASE_DIR / stored_path).resolve()
    attachment_root = EXPERIMENT_RECORD_ATTACHMENTS_DIR.resolve()
    if attachment_root not in candidate.parents:
        return
    try:
        candidate.unlink(missing_ok=True)
    except OSError:
        pass


def render_experiment_records() -> None:
    st.title("実験記録")
    st.write(
        "実験ごとに1つの記録を作成し、主要工程の進行状態、実験結果、コメントを保存します。"
    )

    try:
        store = load_experiment_records(EXPERIMENT_RECORDS_PATH)
    except ValueError as exc:
        st.error(str(exc))
        return

    records = [record for record in store.get("records", []) if isinstance(record, dict)]

    if st.button(
        "新しい実験記録を作成",
        type="primary",
        use_container_width=True,
        key="experiment_record_create",
    ):
        try:
            record = create_experiment_record(store)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state.active_experiment_record_id = record["id"]
            st.session_state.experiment_record_draft = record
            st.rerun()

    active_id = str(st.session_state.get("active_experiment_record_id", ""))
    active_record = next((record for record in records if record.get("id") == active_id), None)
    draft = st.session_state.get("experiment_record_draft")
    if (
        active_record is None
        and isinstance(draft, dict)
        and str(draft.get("id", "")) == active_id
    ):
        active_record = draft

    if active_record:
        st.markdown("### 現在の実験記録")
        st.caption(
            f'実験ID：{active_record.get("id", "")}｜作成：{active_record.get("created_at", "")}'
        )
        process_status = active_record.get("process_status", {})
        existing_condition_report = active_record.get("condition_report")

        with st.form(f'experiment_record_form_{active_record.get("id", "current")}'):
            st.markdown(
                "**「実験条件検討」で作成したカルテがある場合は、こちらに添付してください。**"
            )
            if isinstance(existing_condition_report, dict) and existing_condition_report.get("name"):
                st.caption(f'添付済み：{existing_condition_report.get("name", "")}')
            condition_report_upload = st.file_uploader(
                "実験条件検討カルテ（PDF）",
                type=["pdf"],
                accept_multiple_files=False,
                key=f'experiment_record_condition_report_{active_record.get("id", "current")}',
            )
            droplet_status = st.selectbox(
                "ドロップレット作製",
                PROCESS_STATUS_OPTIONS,
                index=list(PROCESS_STATUS_OPTIONS).index(
                    process_status.get("droplet_creation", "未実施")
                    if process_status.get("droplet_creation", "未実施") in PROCESS_STATUS_OPTIONS
                    else "未実施"
                ),
                key=f'experiment_record_droplet_{active_record.get("id", "current")}',
            )
            sorting_status = st.selectbox(
                "ソーティング・分注",
                PROCESS_STATUS_OPTIONS,
                index=list(PROCESS_STATUS_OPTIONS).index(
                    process_status.get("sorting_dispensing", "未実施")
                    if process_status.get("sorting_dispensing", "未実施") in PROCESS_STATUS_OPTIONS
                    else "未実施"
                ),
                key=f'experiment_record_sorting_{active_record.get("id", "current")}',
            )
            release_status = st.selectbox(
                "破壊",
                PROCESS_STATUS_OPTIONS,
                index=list(PROCESS_STATUS_OPTIONS).index(
                    process_status.get("release", "未実施")
                    if process_status.get("release", "未実施") in PROCESS_STATUS_OPTIONS
                    else "未実施"
                ),
                key=f'experiment_record_release_{active_record.get("id", "current")}',
            )
            current_result = active_record.get("result", "判定不能")
            if current_result not in RESULT_STATUS_OPTIONS:
                current_result = "判定不能"
            result = st.selectbox(
                "実験結果",
                RESULT_STATUS_OPTIONS,
                index=list(RESULT_STATUS_OPTIONS).index(current_result),
                key=f'experiment_record_result_{active_record.get("id", "current")}',
            )
            comment = st.text_area(
                "コメント",
                value=str(active_record.get("comment", "")),
                placeholder="実験について残しておきたい内容を入力してください。",
                height=120,
                key=f'experiment_record_comment_{active_record.get("id", "current")}',
            )
            submitted = st.form_submit_button(
                "記録を保存",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            new_attachment_path = None
            new_condition_report = None
            old_condition_report = (
                dict(existing_condition_report)
                if isinstance(existing_condition_report, dict)
                else None
            )
            try:
                if condition_report_upload is not None:
                    new_condition_report, new_attachment_path = _save_experiment_condition_report(
                        str(active_record.get("id", "")),
                        condition_report_upload,
                    )

                is_saved_record = any(
                    isinstance(record, dict) and record.get("id") == active_record.get("id")
                    for record in store.get("records", [])
                )
                if is_saved_record:
                    saved_record = update_experiment_record(
                        store,
                        active_record["id"],
                        process_status={
                            "droplet_creation": droplet_status,
                            "sorting_dispensing": sorting_status,
                            "release": release_status,
                        },
                        result=result,
                        comment=comment,
                        condition_report=new_condition_report,
                    )
                else:
                    saved_record = add_experiment_record(
                        store,
                        active_record,
                        process_status={
                            "droplet_creation": droplet_status,
                            "sorting_dispensing": sorting_status,
                            "release": release_status,
                        },
                        result=result,
                        comment=comment,
                        condition_report=new_condition_report,
                    )
                save_experiment_records(EXPERIMENT_RECORDS_PATH, store)
            except ValueError as exc:
                if new_attachment_path is not None:
                    try:
                        new_attachment_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                st.error(str(exc))
            else:
                if new_condition_report is not None and old_condition_report:
                    _remove_experiment_condition_report_file(old_condition_report)
                st.session_state.active_experiment_record_id = saved_record["id"]
                st.session_state.experiment_record_draft = None
                records = [
                    record for record in store.get("records", []) if isinstance(record, dict)
                ]
                active_record = saved_record
                st.success("実験記録を保存しました。")

        if st.button(
            "← 直前のページに戻る",
            use_container_width=True,
            key="experiment_record_return_previous",
        ):
            return_page = str(
                st.session_state.get("experiment_record_return_page", "home")
            )
            if not return_page or return_page == "experiment_records":
                return_page = "home"
            st.session_state.page = return_page
            request_scroll_to_top()
            st.rerun()

    st.markdown("### 記録一覧")
    if not records:
        st.info("保存された実験記録はまだありません。")
        return

    for record in sorted(records, key=lambda item: str(item.get("created_at", "")), reverse=True):
        record_id = str(record.get("id", ""))
        result_label = str(record.get("result", "判定不能"))
        created_at = str(record.get("created_at", ""))
        with st.expander(f"{record_id}｜{result_label}｜{created_at}", expanded=False):
            status = record.get("process_status", {})
            st.write(f'ドロップレット作製：{status.get("droplet_creation", "未実施")}')
            st.write(f'ソーティング・分注：{status.get("sorting_dispensing", "未実施")}')
            st.write(f'破壊：{status.get("release", "未実施")}')
            st.write(f'実験結果：{result_label}')
            comment_text = str(record.get("comment", "")).strip()
            st.write(f'コメント：{comment_text if comment_text else "なし"}')
            if st.button(
                "この記録を開く",
                key=f"experiment_record_open_{record_id}",
                use_container_width=True,
            ):
                st.session_state.active_experiment_record_id = record_id
                st.session_state.experiment_record_draft = None
                request_scroll_to_top()
                st.rerun()


def render_experiment_condition_advisor() -> None:
    render_experiment_condition_advisor_page(
        navigation_version=VERSION,
        product_catalog=PRODUCT_CATALOG,
        product_matcher=find_droplet_product_candidates,
    )


def render_account_setup() -> None:
    device_labels = {
        "selector": "On-chip Droplet Selector",
        "sort": "On-chip Sort",
    }
    device = st.session_state.get("account_setup_device", "selector")
    st.title("アカウントの設定方法")
    st.caption(device_labels.get(device, "On-chip Droplet Selector / On-chip Sort"))
    st.info("工事中です。")
    if st.button("← 工程に戻る", type="primary"):
        st.query_params.clear()
        st.session_state.page = "guide"
        request_scroll_to_top()
        st.rerun()


def render_complete() -> None:
    st.title("お疲れ様でした")
    st.success("以上で作業は終了となります。")
    if st.session_state.workflow_key.startswith("dg"):
        st.write("作製物の回収、チューブの表示、保存または次工程の条件、装置と温調ユニットの停止を確認してください。")
    elif st.session_state.workflow_key.startswith("recovery_"):
        st.write("ドロップレットが十分に破壊され、内容物が培地相へ戻っていることと、次工程に使用するサンプルを確保できていることを確認してください。")
    else:
        st.write("必要なデータが正しく保存されていることを確認してください。")
    if st.button(
        "実験記録",
        type="primary",
        use_container_width=True,
        key=f"complete_experiment_records_{st.session_state.workflow_key}",
    ):
        open_experiment_records()
    if st.button(
        "トップページに戻る",
        use_container_width=True,
        key=f"complete_back_home_{st.session_state.workflow_key}",
    ):
        go("home")


init_state()
apply_query_navigation()
render_sidebar()
if st.session_state.page == "home":
    render_home()
elif st.session_state.page == "dg_setup":
    render_dg_setup()
elif st.session_state.page == "sorting_setup":
    render_sorting_setup()
elif st.session_state.page == "recovery_setup":
    render_recovery_setup()
elif st.session_state.page == "guide":
    render_guide()
elif st.session_state.page == "complete":
    render_complete()
elif st.session_state.page == "trouble":
    render_trouble()
elif st.session_state.page == "results":
    render_results()
elif st.session_state.page == "products":
    render_products()
elif st.session_state.page == "glossary":
    render_glossary()
elif st.session_state.page == "experiment_condition_advisor":
    render_experiment_condition_advisor()
elif st.session_state.page == "experiment_records":
    render_experiment_records()
elif st.session_state.page == "account_setup":
    render_account_setup()
else:
    go("home")

apply_glossary_hover(enabled=st.session_state.page in GLOSSARY_HOVER_PAGES)
apply_scroll_to_top()
