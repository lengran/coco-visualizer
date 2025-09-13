# coco-visualizer
This is a tool to merge the coco annotations into the dataset images. The script supports both single image processing and bulk processing.

Usage:

Please convert this to a github markdown table.

| -s | --single-image | Whether the input_path pointing to a single image or a directory of images. (default: False)|
| -i | --input-path | Single image mode: Path to the image file.\nBulk mode: Path to the directory containing the image files.|
| -c | --coco-path | Path to the coco.json file. (optional: if coco.json locates in input-path and you are not in single-image mode)|
| -o | --output-path | Single image mode: Path to the generated image. Bulk mode: Path to the directory storing the generated images.|
| -f | --force | Whether the program should keep running when encountering errors. (default: True)|
| -v | --verbose | Whether the program should print the errors. (default: True)|
| -p | --num-process | Number of processes to use while processing images. (Default: Number of your cpu cores)|
| -m | --mask-margin-width | The width of mask's margin. Set it to 0 (default) to disable generation of masked images.|