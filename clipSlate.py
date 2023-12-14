import os
import sys
import argparse
import time
import subprocess
from PIL import Image, ImageDraw, ImageFont
import tempfile
import filetype

# Setup
temp_dir = tempfile.TemporaryDirectory()
class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

def ask_clip_path():
    file_or_dir = input('Would you like to choose a [f]ile, [d]irectory of clips? (or [q] to quit) ').lower()
    if file_or_dir == 'f':
        # single file
        isFile = False
        while not isFile:
            submitted = input('Please type in the path to the clip or [q] to quit): ')
            if submitted == "q":
                end_clean()
            else:
                target_path = is_valid_path(submitted)
                if target_path:
                    return(target_path)
                    isFile = True
    elif file_or_dir =='d':
        # directory of files
        tell_user('Directory functionality is still in progress. Sorry for the inconvenience.')
        end_clean()
    else:
        end_clean()

def is_valid_path(path):
    target_path = os.path.abspath(path)
    isFile = os.path.isfile(target_path)
    if isFile:
        return target_path
    else:
        return False

def clean_path(path):
    cleaned_path = path.replace("\ ", " ")
    return cleaned_path

def is_video(path):
    kind = filetype.guess(path)
    if kind.mime[:5] == "video":
        return True
    else:
        return False

def get_clip_info(path):
    clip_name, clip_ext = os.path.splitext(os.path.basename(path))
    tell_user("Getting info on video " + clip_name + clip_ext,"hold")
    cmd = 'ffprobe -v error -select_streams v -count_packets -show_entries stream=width,height,duration,nb_read_packets,r_frame_rate -of csv=p=0 "' + path + '"'
    cmd_result = subprocess.check_output(cmd,shell=True,stderr=subprocess.DEVNULL).rstrip().decode('UTF-8')
    result = cmd_result.split(',')

    clip_trt = float(result[3])
    min_sec = time.strftime("%Mm%Ss", time.gmtime(clip_trt))
    directory = clean_path(os.path.dirname(path))
    tell_user('DONE','done')
    return {'name':clip_name,
            'ext':clip_ext,
            'path':path,
            'directory':directory,
            'width':int(result[0]),
            'height': int(result[1]),
            'framerate':result[2],
            'trt': clip_trt,
            'frames':int(result[4]),
            'min_sec':min_sec}

def extract_images(clip_info,segment_length):
    tell_user(("Grabbing thumbnails from clip " + clip_info['name'] + clip_info['ext']), type='hold')
    img_to_extract = ''
    for x in range(100, clip_info["frames"], segment_length):
        img_to_extract += '+eq(n\\,' + str(x) + ')'
    cmd = f'ffmpeg -i "{clip_info['path']}" -vf select="{img_to_extract}" -fps_mode passthrough "{temp_dir.name}/thumbnail_%d.jpg"'
    result = subprocess.run(cmd,shell=True,stderr=subprocess.DEVNULL)
    tell_user("DONE",'done')

def make_slate_1(clip_info):
    # Note, this builds it as a 1920x1080, then resizes it at the end.
    slate = Image.new("RGB", (1920,1080), (0,0,0)).convert("RGBA")

    # Extract Images
    tot_stills = 6
    segment_length = int(clip_info["frames"] / tot_stills)
    extract_images(clip_info,segment_length)

    # compile thumbnails
    tell_user("Placing thumbnails", type='hold')

    imgs_path = []
    paste_coords = ((0, 360), (640, 360), (1280, 360), (0, 720), (640, 720), (1280, 720))

    for x in range(0,tot_stills):
        tmpImg = Image.open(temp_dir.name + '/' + 'thumbnail_' + str(x+1) + '.jpg')
        tmpResized = tmpImg.resize((640,360))
        slate.paste(tmpResized,paste_coords[x])
    
    tell_user("DONE",'done')

    # add text
    tell_user("Adding title and trt to clipSlate", type='hold')
    font_label = ImageFont.truetype('Arial Narrow.ttf', 50)
    font_title = ImageFont.truetype('Arial Narrow.ttf', 85)
    font_trt = ImageFont.truetype('Arial Narrow.ttf', 250)
    title_linebreaked = insert_newlines(clip_info['name'])
    if len(title_linebreaked) > 89:
        title_linebreaked = title_linebreaked[:92] +'...'
    draw = ImageDraw.Draw(slate)
    draw.text((96, 45), "title", font=font_label, fill='#666666')
    draw.text((1786, 45), "trt", font=font_label, fill='#666666')
    draw.text((1099, 52), clip_info["min_sec"], font=font_trt,fill='#FFBD00')
    draw.text((96, 88), title_linebreaked, font = font_title, fill='#CDCDCD')

    # Add Watermark
    txt_image = Image.new('RGBA', (1920,1080), (255,255,255,0))
    draw_text = ImageDraw.Draw(txt_image) 
    font_madewith = ImageFont.truetype('Arial.ttf', 15)
    font_clipslate = ImageFont.truetype('Arial.ttf', 35)
    draw_text.text((1760, 1000), "made with", font=font_madewith,  fill='#ffffff20')
    draw_text.text((1760, 1010), "clipSlate", font=font_clipslate, fill='#ffffff10')
    final_slate = Image.alpha_composite(slate, txt_image) 
    
    # Resize to the final video size
    final_slate.thumbnail((clip_info["width"], clip_info["height"]))
    final_slate = final_slate.convert("RGB")
    
    # Save
    slate_path = f'{clip_info['directory']}/{clip_info['name']}_slate.jpg'
    final_slate.save(slate_path, quality=95)
    tell_user('DONE','done')
    tell_user('clipSlate saved to: ' + slate_path,'info')

    return slate_path

def encode_clip(clip_info,slate_path):
     # Insert into video
    tell_user('Transcoding video. This might take a while. ' + color.YELLOW + 'Please be patient!' + color.END, '')
    cmd = f'ffmpeg -y -i "{clip_info['path']}" -i "{slate_path}" -filter_complex "overlay=0:0:enable=\'between(t,0,.01)\'" -preset fast -c:a copy "{clip_info['directory']}/{clip_info['name']}_clipslate{clip_info['ext']}"'
    cmd_result = subprocess.check_output(cmd,shell=True,stderr=subprocess.DEVNULL)
    tell_user('Clip encoding','hold')
    tell_user('DONE','done')

def insert_newlines(string, every=30):
    return '\n'.join(string[i:i+every] for i in range(0, len(string), every))    

def tell_user(msg = '',type = ''):
    preface = color.BOLD + '[clipSlate] '+ color.END
    if type.lower() == "hold":
        print(f'{preface} {msg}...',end='')
    elif type.lower() == "info":
        print(f'{preface} {color.BLUE}{msg}{color.END}')
    elif type.lower() == "alert":
        print(f'{preface} {color.YELLOW}{msg}{color.END}')
    elif type.lower() == "warn":
        print(f'{preface} {color.RED}{msg}{color.END}')
    elif type.lower() == "done":
        print(color.GREEN + msg + color.END)
    else:
        print(f'{preface} {msg}')

def end_clean():
    temp_dir.cleanup()
    tell_user('All done!\n')
    sys.exit()

def main():
    parser = argparse.ArgumentParser(description='Creates a clipSlate, and optionally adds it to the clip.')
    parser.add_argument('-f', dest='file', action='store', type=str, help='The file to process.')
    parser.add_argument('-e', dest='encode',help="Encode the target file with the clipSlate", action='store_true')

    # get the path to the target object (either by -f or by asking)
    args = parser.parse_args()
    args.file = clean_path(args.file)

    if args.file == None:
        clip_path = ask_clip_path()
    else:
        if is_valid_path(args.file):
            clip_path = os.path.abspath(args.file)
        else:
            tell_user('The file ' + args.file + ' was not found.','warn')
            end_clean()

    if not is_video(clip_path):
        tell_user('This is not a video clip.','warn')
        end_clean()

    # # We have a valid clip. Do all the stuff.
    clip_info = get_clip_info(clip_path)
    # Returns: clip_info[variable]  variables: name, ext, path, directory, width, height, framerate, frames, trt, min_sec

    slate_path = make_slate_1(clip_info)

    # # should we encode?
    if args.encode:
        encode_clip(clip_info, slate_path)
    else:
        tell_user("Note: The clipSlate WASN'T added into the clip. Include '-e' if you want to do it.",'alert')

    end_clean()

if __name__ == "__main__":
    # Startup
    print(f'\n{color.BOLD}clipSlate{color.END}')
    print('---------')
    print('v1.0, by TC Conway, IW Studios\n')
    print(f"DEBUG: Temp Dir: {temp_dir.name}")

    main()