import json
import os
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import argparse
import glob
import shutil
import ast
import time
from multiprocessing import Pool, TimeoutError
import multiprocessing

def ExtractImageIDFromImageFile(filename: str, coco_data: object, force: bool = True, verbose: bool = True) -> int:
    '''
    Extract the image_id of a given image file from coco.json.
    Input:
        filename: The name part (without path) of a image file.
        coco_data: The python object loaded from a coco.json file.
        force: If set to false, the program might exit when error occurs. Would be useful when run in bulk mode.
        verbose: If set to true, error messages will be printed.
    Output:
        image_id (int) in coco.json or None.
    '''
    error_msg = f"Cannot find '{filename}' in coco.json."
    if "images" not in coco_data:
        if force:
            if verbose:
                print(error_msg)
            return None
        else:
            raise ValueError(error_msg)

    for image in coco_data["images"]:
        if image["file_name"] != filename:
            continue
        else:
            return image["id"]
    if force:
        if verbose:
            print(error_msg)
        return None
    else:
        raise ValueError(error_msg)


def DrawCocoBoxes(coco_data: object, image_path: str, output_path: str, masked_margin_width: int = 0, force: bool = True, verbose: bool = True) -> bool:
    """
    Merge the annotation boxs into the images.
    Input:
        coco_data: The json object created from coco.json.
        image_path: Path to an image.
        output_path: Path to write the merged image.
        masked_margin: If a masked output is needed, set this to the width of the margin area.
        force: If set to false, the program might exit when error occurs. Would be useful when run in bulk mode.
        verbose: If set to true, error messages will be printed.
    Output:
        True or exceptions.
    """
    # Check if image has annotation
    image_id = ExtractImageIDFromImageFile(Path(image_path).name, coco_data, force, verbose)
    if image_id is None:                                                                # force should be true, or the program would already be dead 
        return False

    has_annotation = False
    if 'annotations' in coco_data:
        annotations_drawn_count = 0
        for annotation in coco_data['annotations']:
            if annotation['image_id'] == image_id:
                has_annotation = True
                break
    if not has_annotation:
        return False

    # Read the image file
    image = Image.open(image_path)
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    draw = ImageDraw.Draw(image)

    if masked_margin_width > 0:
        # original_image = Image.open(image_path)
        mask = Image.new("L", image.size, 0)
        masked_draw = ImageDraw.Draw(mask)

    # Draw annotation boxes
    if 'annotations' in coco_data:
        annotations_drawn_count = 0
        for annotation in coco_data['annotations']:
            if annotation['image_id'] == image_id: 
                # Get a bbox
                if 'bbox' not in annotation:
                    if verbose:
                        print(f"There is no bboxes in annotaion {annotation["id"]}.")
                    continue
                bbox = annotation['bbox']
                if len(bbox) < 4:
                    if verbose:
                        print(f'There are bbox instance with less than 4 numbers in annotation {annotation["id"]}.')
                    continue
                x, y, w, h = bbox
                top_left = (x, y)
                bottom_right = (x + w, y + h)
                
                
                # Draw the box
                draw.rectangle([top_left, bottom_right], outline="red", width=2)

                left_boundary = x - masked_margin_width
                if left_boundary < 0:
                    left_boundary = 0
                right_boundray = x + w + masked_margin_width
                if right_boundray > image.size[0]:
                    right_boundray = image.size[0]
                upper_boundary = y - masked_margin_width
                if upper_boundary < 0:
                    upper_boundary = 0
                lower_boundary = y + h + masked_margin_width
                if lower_boundary > image.size[1]:
                    lower_boundary = image.size[1]
                
                # Add category label
                if 'category_id' in annotation and 'categories' in coco_data:
                    category_id = annotation['category_id']
                    category_name = next(
                        (category['name'] for category in coco_data['categories'] if category['id'] == category_id),
                        f"Class {category_id}"
                    )
                    
                    # Dynamically set font size
                    dyn_fontsize = int((lower_boundary - upper_boundary) * 0.15)
                    if dyn_fontsize < 10:
                        dyn_fontsize = 5
                    dyn_offset = int(dyn_fontsize * 1.25)
                    if y - dyn_offset < 0:
                        dyn_offset = y
                    dyn_font = ImageFont.load_default(dyn_fontsize)

                    text_bbox = draw.textbbox((x, y - dyn_offset), category_name, font=dyn_font)
                    draw.rectangle(text_bbox, fill="red")
                    draw.text((x, y - dyn_offset), category_name, fill="white", font=dyn_font)
                
                annotations_drawn_count += 1

                # Update the masked version
                if upper_boundary > y - dyn_offset:
                    upper_boundary = y - dyn_offset                                     # Make sure the label is visible

                if masked_margin_width > 0:
                    masked_draw.rectangle([(left_boundary, upper_boundary), (right_boundray, lower_boundary)], fill=255)


    else:
        error_msg = f"Error: There is no annotation in given coco.json."
        if not force:
            raise ValueError(error_msg)
        elif verbose:
            print(error_msg)
            return False
    
    # Check if there exists a workplace boundary, if so, draw it.
    '''
        The defining txt file is composed in the following format.

         1/0;  [[x1,y1],[x2,y2],[x3,y3],[x4,y4]];   ......
        -----  ---------------------------------    ------
          |                    |                       |
        label          the defination box           other stuff
    '''
    boundary_file_path = os.path.splitext(image_path)[0] + '.txt'
    if os.path.isfile(boundary_file_path):
        try:
            with open(boundary_file_path, 'r') as file:
                content = file.read()

                parts = content.split(';')
                if len(parts) < 2:
                    error_msg = f"The file {boundary_file_path} does not contain enough parts separated by semicolons."
                    if not force:
                        raise ValueError(error_msg)
                    elif verbose:
                        print(error_msg)
                        return False
                
                # Extract the box info
                second_part = parts[1].strip()
                nested_list = ast.literal_eval(second_part)                             # Convert the string representation of the nested list to an actual list

                # Validate the box info and draw the workspace boundary
                if isinstance(nested_list, list) and len(nested_list) == 4 \
                    and isinstance(nested_list[0], list) and len(nested_list[0]) == 2 \
                    and isinstance(nested_list[1], list) and len(nested_list[1]) == 2 \
                    and isinstance(nested_list[2], list) and len(nested_list[2]) == 2 \
                    and isinstance(nested_list[3], list) and len(nested_list[3]) == 2: 
                    top_left = (nested_list[0][0], nested_list[0][1])
                    bottom_right = (nested_list[2][0], nested_list[2][1])
                    
                    draw.rectangle([top_left, bottom_right], outline="blue", width=2)
                else:
                    error_msg = f"The second part of file {boundary_file_path} is not a valid nested list."
                    if not force:
                        raise ValueError(error_msg)
                    elif verbose:
                        print(error_msg)
                        return False

        except FileNotFoundError:
            print("The specified file was not found.")
        except SyntaxError:
            print("There was a syntax error in the nested list format.")
        except Exception as e:
            print(f"An error occurred: {e}")
    
    # Save the images to designated place.
    image.save(output_path)
    if masked_margin_width > 0:
        masked_image = Image.composite(image, Image.new("RGB", image.size, (0, 0, 0)), mask)
        masked_image_path = os.path.splitext(output_path)[0] + "_masked.jpg"
        masked_image.save(masked_image_path)
    
    return True

def GetAllSubDirectories(dir_path: str, force: bool = True, verbose: bool = True) -> list:
    '''
    Generate a list containing the folder itself and all its subfolders.
    Input:
        dir_path: Path to the target directory.
        force: If set to false, the program might exit when error occurs. Would be useful when run in bulk mode.
        verbose: If set to true, error messages will be printed.
    Output:
        A list of directories or none.
    '''
    try:
        abs_path = os.path.abspath(dir_path)
        if not os.path.exists(dir_path):
            raise FileNotFoundError(f"The path doesn't exist: {abs_path}")
        if not os.path.isdir(abs_path):
            raise NotADirectoryError(f"The path isn't a directory: {abs_path}")
        
        dir_list = []
        dir_list.append(abs_path)
        for root, dirs, files in os.walk(abs_path):
            for dir_name in dirs:
                folder_path = os.path.join(root, dir_name)
                dir_list.append(folder_path)
        
        return dir_list
    
    except Exception as e:
        if not force:
            raise e
        elif verbose:
            print(f"Error: {e}")
            return None

def CreateDirectorySafely(directory_path: str, max_retries: int = 3, retry_delay: int = 1, auto_delete: bool = False, force: bool = True, verbose: bool = True) -> bool:
    """
    Create a directory safely.
    
    Input:
        directory_path: The directory to create.
        max_retries: A maximum times of retries
        retry_delay: Time interval between retries.
        auto_delete: If the directory already exists, whether the old one should be deleted.
        force: If set to false, the program might exit when error occurs. Would be useful when run in bulk mode.
        verbose: If set to true, error messages will be printed.
    Output:
        True or False.
    """
    for attempt in range(max_retries):
        try:
            # Check if the directory exists.
            abs_path = os.path.abspath(directory_path)
            if os.path.exists(abs_path):
                if auto_delete:
                    if verbose:
                        print(f"The directory [{abs_path}] already exists. Deleting...")
                    shutil.rmtree(abs_path)
                    if verbose:
                        print(f"The directory [{abs_path}] has been deleted.")
                else:
                    # error_str_file_exist = f"The target directory already exists: {abs_path}"
                    # if verbose:
                    #     print(error_str_file_exist)
                    # return False
                    return True
            
            # Create the directory.
            os.makedirs(abs_path)
            return True
            
        except PermissionError:
            if verbose:
                print(f"You don't have the permission to operate on the directory. Retrying: [{attempt + 1}/{max_retries}].")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                error_msg = f"After {max_retries} retries, still cannot create the directory: {abs_path}"
                if not force:
                    raise ValueError(error_msg)
                elif verbose:
                    print(error_msg)
                    return False
                
        except Exception as e:
            error_msg = f"An error happened when creating the directory[{abs_path}]: {e}"
            if not force:
                raise ValueError(error_msg)
            elif verbose:
                print(error_msg)
                return False
    return False

def ProcessImages(coco_data: object, image_files: list, subdir: str, input_path:str, output_path: str, mask_margin_width:int, force: bool = True, verbose: bool = True):
    output_dir = os.path.join(output_path, os.path.relpath(subdir, input_path))
    if not os.path.exists(output_dir) or not os.path.isdir(output_dir):
        if not CreateDirectorySafely(output_dir):
            error_msg = f"Cannot create output directory: {output_dir}"
            if not force:
                raise ValueError(error_msg)
            else:
                if verbose:
                    print(error_msg)
                exit(-4)

    for image_path in image_files:
        img_output_path = os.path.join(output_path, os.path.relpath(image_path, input_path))
        DrawCocoBoxes(coco_data, image_path, img_output_path, mask_margin_width, force, verbose)

if __name__ == "__main__":
    # Support commandline parameters
    parser = argparse.ArgumentParser(description="This is a tool to merge the coco annotations into the dataset images. The script supports both single image processing and bulk processing.")
    parser.add_argument("-s", "--single-image", type=bool, default=False, required=False, metavar="", help="Whether the input_path pointing to a single image or a directory of images. (default: False)")
    parser.add_argument("-i", "--input-path", type=str, required=True, metavar="", help="Single image mode: Path to the image file.\nBulk mode: Path to the directory containing the image files.")
    parser.add_argument("-c", "--coco-path", type=str, required=False, default=None, metavar="", help="Path to the coco.json file. (optional: if coco.json locates in input-path and you are not in single-image mode)")
    parser.add_argument("-o", "--output-path", type=str, required=True, metavar="", help="Single image mode: Path to the generated image. Bulk mode: Path to the directory storing the generated images.")
    parser.add_argument("-f", "--force", type=bool, default=True, required=False, metavar="", help="Whether the program should keep running when encountering errors. (default: True)")
    parser.add_argument("-v", "--verbose", type=bool, default=True, required=False, metavar="", help="Whether the program should print the errors. (default: True)")
    parser.add_argument("-p", "--num-process", type=int, default=0, required=False, metavar="", help="Number of processes to use while processing images. (Default: Number of your cpu cores)")
    parser.add_argument("-m", "--mask-margin-width", type=int, default=0, required=False, metavar="", help="The width of mask's margin. Set it to 0 (default) to disable generation of masked images.")
    args = parser.parse_args()

    # Check invalid num_process parameters
    suggested_num_threads = int(len(os.sched_getaffinity(0)) / 2)                                        # Take hyperthreading into account, use half the number of logical processors.
    num_threads = suggested_num_threads
    if args.num_process < 0:
        if not args.force:
            raise ValueError(f"Using {args.num_process} processes is not supported.")
        elif args.verbose:
            print(f"Using {args.num_process} processes is not supported. Will use {num_threads} threads.")
    elif args.num_process > 0:
        num_threads = args.num_process

    # Check invalid input_path
    if not os.path.exists(args.input_path):
        print(f"Input path doesn't exist: {args.input_path}")                           # One can't force it to run without input, can you?
        exit(-1)
    if not args.single_image and not os.path.isdir(args.input_path):
        print(f"The input-path doesn't point to a directory but a file. Do you want to run this program in single-image mode?")
        exit(-1)

    # Read coco.json
    coco_path = None
    if args.coco_path == None and not args.single_image:
        coco_path = os.path.join(args.input_path, "coco.json")
    else:
        raise ValueError(f"Cannot find coco.json at {coco_path}")
    coco_data = None
    try:
        with open(coco_path, 'r') as coco_file:
            coco_data = json.load(coco_file)
    except FileNotFoundError:                                                           # One can't force it to run without input, can you?
        print(f"Cannot find the coco.json file at: {args.coco_path}")
        exit(-2)
    except json.JSONDecodeError:
        print("Error decoding coco.json. Please check if it's a json file.")
        exit(-2)
    except Exception as e:
        print(f"An error occurred when loading coco.json: {e}")
        exit(-2)

    # Read and process one image
    if args.single_image == True:
        output_dir = os.path.dirname(args.output_path)
        if not os.path.exists(output_dir) or not os.path.isdir(output_dir):
            if not CreateDirectorySafely(output_dir):
                error_msg = f"Cannot create output directory: {output_dir}"
                if not args.force:
                    raise ValueError(error_msg)
                else:
                    if args.verbose:
                        print(error_msg)
                    exit(-3)
        
        DrawCocoBoxes(coco_data, args.input_path, )
        

    # Read and process image in bulk + multiprocess mode
    else:
        if not os.path.exists(args.output_path) or not os.path.isdir(args.output_path):
            if not CreateDirectorySafely(args.output_path):
                print(f"Failed to create the output directory: {args.output_path}")
                exit(-4)

        directories = GetAllSubDirectories(args.input_path)

        # Find images
        image_files = list()
        for subdir in directories:
            search_pattern_jpg = os.path.join(subdir, "*.jpg")
            jpg_files = glob.glob(search_pattern_jpg, recursive=False)
            search_pattern_png = os.path.join(subdir, "*.png")
            png_files = glob.glob(search_pattern_png, recursive=False)
            search_pattern_jpeg = os.path.join(subdir, "*.jpeg")
            jpeg_files = glob.glob(search_pattern_jpeg, recursive=False)
            
            sub_image_files = jpg_files + png_files + jpeg_files
            image_files = image_files + sub_image_files
            if args.verbose:
                print(f"Found {len(sub_image_files)} images in directory {subdir}")
        
        # Process images using python's multiprocess module
        if args.verbose:
            print(f"Found {len(image_files)} images to process. Use {args.num_process} processes to process them...")
        child_process = list()

        shard_size = int(len(image_files) / args.num_process)
        for i in range(args.num_process - 1):
            p = multiprocessing.Process(target=ProcessImages, args=(coco_data, image_files[shard_size * i: shard_size * (i + 1)], subdir, args.input_path, args.output_path, args.mask_margin_width, args.force, args.verbose,))
            p.start()
            child_process.append(p)
        last_p = multiprocessing.Process(target=ProcessImages, args=(coco_data, image_files[shard_size * (args.num_process - 1):], subdir, args.input_path, args.output_path, args.mask_margin_width, args.force, args.verbose, ))
        last_p.start()
        child_process.append(last_p)

        process_count = 0
        for p in child_process:
            p.join()
            process_count = process_count + 1
            if args.verbose:
                print(f"Process {process_count} has finished.")

        if args.verbose:
            print("Done!")