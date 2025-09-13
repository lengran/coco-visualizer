# coco-visualizer
This is a tool to merge the coco annotations into the dataset images. The script supports both single image processing and bulk processing.

Usage:

| Short | Long                | Description                                                                                                              | Default                  |
|-------|---------------------|--------------------------------------------------------------------------------------------------------------------------|--------------------------|
| -s    | --single-image      | Whether the input_path points to a single image or a directory of images.                                                | False                    |
| -i    | --input-path        | Single image mode: Path to the image file.<br>Bulk mode: Path to the directory containing the image files.                | —                        |
| -c    | --coco-path         | Path to the coco.json file. (optional: if coco.json is located in input-path and you are not in single-image mode)        | —                        |
| -o    | --output-path       | Single image mode: Path to the generated image.<br>Bulk mode: Path to the directory storing the generated images.         | —                        |
| -f    | --force             | Whether the program should keep running when encountering errors.                                                         | True                     |
| -v    | --verbose           | Whether the program should print the errors.                                                                             | True                     |
| -p    | --num-process       | Number of processes to use while processing images.                                                                      | Number of CPU cores      |
| -m    | --mask-margin-width | The width of mask's margin. Set it to 0 to disable generation of masked images.                                           | 0                        |
