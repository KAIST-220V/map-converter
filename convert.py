import pyproj
from shapely.geometry import Polygon
import math
import json
from PIL import Image, ImageDraw
from statistics import mean
import os

# no limit on the image size
Image.MAX_IMAGE_PIXELS = None

# mark image center with small circle
def mark_center_in_image(image_path):
    
    img = Image.open(image_path)
    width, height = img.size

    center_x = width // 2
    center_y = height // 2

    circle_radius = int(min(width, height) * 0.001)

    draw = ImageDraw.Draw(img)

    draw.ellipse(
        (center_x - circle_radius, center_y - circle_radius,
         center_x + circle_radius, center_y + circle_radius),
        fill="red", outline="red"
    )

    image_paths = image_path.split('/')
    image_paths[len(image_paths) - 1] = image_paths[len(image_paths) - 1].replace('.', f'_mark_center.')

    new_file_path = '/'.join(image_paths)
    
    img.save(new_file_path)
    print(f"Image saved as {new_file_path}")

def mark_x_y_in_image(image_path, x, y):
    img = Image.open(image_path)
    width, height = img.size

    circle_radius = int(min(width, height) * 0.001)

    draw = ImageDraw.Draw(img)

    draw.ellipse(
        (x - circle_radius, y - circle_radius,
         x + circle_radius, y + circle_radius),
        fill="red", outline="red"
    )

    image_paths = image_path.split('/')
    image_paths[len(image_paths) - 1] = image_paths[len(image_paths) - 1].replace('.', f'_mark_({x}, {y}).')

    new_file_path = '/'.join(image_paths)
    
    img.save(new_file_path)
    print(f"Image saved as {new_file_path}")

# get image width, height in px size
def get_image_px_info(image_path):

    image = Image.open(image_path)
    width, height = image.size

    return width, height

# convert GRS80 coordinate point into the lat & lon
def convert_GRS(lat_0, lon_0, x_0, y_0, x_tm, y_tm):

    tm_projection = pyproj.Proj(proj="tmerc", ellps="GRS80", k=1, lat_0=lat_0, lon_0=lon_0, x_0=x_0, y_0=y_0)

    lon, lat = tm_projection(x_tm, y_tm, inverse=True)

    lat_dd = round(lat, 8)
    lon_dd = round(lon, 8)

    return lat_dd, lon_dd

# get the lat & lon of the point after moving
# Note : The direction is (+x, -x, +y, -y) == (East, West, *South, *North)
def move_point(x_amount, y_amount, current_lat, current_lon, image_resolution):

    EARTH_UNIT_LENGTH = 111320

    # diff amount in meter
    x_diff_in_meter = x_amount * image_resolution
    y_diff_in_meter = (-1) * y_amount * image_resolution # direction change

    # 1 degree in lat == about EARTH_UNIT_LENGTH meter
    lat_diff = y_diff_in_meter / EARTH_UNIT_LENGTH

    # 1 degree in lon == about (EARTH_UNIT_LENGTH * cos{latitude}) meter
    lon_diff = x_diff_in_meter / (EARTH_UNIT_LENGTH * math.cos(math.radians(current_lat)))

    new_lat = current_lat + lat_diff
    new_lon = current_lon + lon_diff

    return new_lat, new_lon


# get lat & lon of the origin point (left-top edge)
def get_origin_point(center_lat, center_lon, image_width_px, image_height_px, image_resolution):
    return move_point((-1) * (image_width_px // 2), (-1) * (image_height_px // 2), center_lat, center_lon, image_resolution)

# get lat & lon of the (x,y)
def get_x_y(x, y, origin_lat, origin_lon, image_resolution):
    return move_point(x, y, origin_lat, origin_lon, image_resolution)

# get area of the polygon
def get_area_of_polygon(lat_lon_list):
    # UTM Zone 52N : convert coordinate
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32652", always_xy=True)
    projected_points = [transformer.transform(lon, lat) for lat, lon in lat_lon_list]
    if len(projected_points) < 4:
        print(projected_points)
    polygon = Polygon(projected_points)
    area_m2 = polygon.area  # m^2 unit
    
    return area_m2

# Convert the given input JSON to ouput JSON using the photo and its metadata
# Note. The "image_id" of the input MUST be same with that of the photo and metadata.
# E.g. ("image_id" : "12345") & (12345.tif, 12345.json)
def convert_xy_to_lat_lon(input_json_path, input_image_dir, metadata_dir, output_json_dir):

    # get image id
    with open(input_json_path, 'r', encoding='utf-8') as file:
        input_json = json.load(file)
    
    image_id = input_json['image_id']

    if image_id.endswith('.tif'):
        image_id = image_id[:-4]

    # compare width, height of the image with input JSON data
    input_image_path = f"{input_image_dir}/{image_id}.tif"
    image_width, image_height = get_image_px_info(input_image_path)
    given_width = input_json['image_size']['width']
    given_height = input_json['image_size']['height']

    if (image_height != given_height) or (image_width != given_width):
        # print("Failed to convert : the given image size is different from the input JSON.")
        # print(f" - Given size : {given_width, given_height}")
        # print(f" - Actual size : {image_width, image_height}")
        pass

    # get metadata
    metadata_path = f'{metadata_dir}/{image_id}.json'
    with open(metadata_path, 'r', encoding='utf-8') as file:
        metadata_json = json.load(file)
    
    lat_0 = metadata_json['lat_0']
    lon_0 = metadata_json['lon_0']
    x_0 = metadata_json['x_0']
    y_0 = metadata_json['y_0']
    x_tm = metadata_json['x_tm']
    y_tm = metadata_json['y_tm']
    image_resolution = metadata_json['image_resolution']

    # formatting input JSON
    panel_list_xy = []
    for data in input_json['panel']:
        # get mean
        mean_x = mean(data['shape_attributes']['all_points_x'])
        mean_y = mean(data['shape_attributes']['all_points_y'])
        # make tuples
        xy_list = list(zip(data['shape_attributes']['all_points_x'], data['shape_attributes']['all_points_y']))
        new_item = {
            'mean_point' : (mean_x, mean_y),
            'all_points' : xy_list
        }
        panel_list_xy.append(new_item)

    # get center of the image in lat / lon format
    center_lat, center_lon = convert_GRS(lat_0, lon_0, x_0, y_0, x_tm, y_tm)

    # get origin
    origin_lat_lon = get_origin_point(center_lat, center_lon, image_width, image_height, image_resolution)

    # convert
    panel_list_lat_lon = []
    for xy_data in panel_list_xy:
        new_item = {}
        new_item['mean_point'] = get_x_y(xy_data['mean_point'][0], xy_data['mean_point'][1], origin_lat_lon[0], origin_lat_lon[1], image_resolution)
        xy_list_lat_lon = []
        for xy_point in xy_data['all_points']:
            xy_to_lat_lon = get_x_y(xy_point[0], xy_point[1], origin_lat_lon[0], origin_lat_lon[1], image_resolution)
            xy_list_lat_lon.append(xy_to_lat_lon)
        new_item['all_points'] = xy_list_lat_lon
        panel_list_lat_lon.append(new_item)

    # get area (m^2)
    area_list = []
    filtered_panel_list_lat_lon = []

    for panel_info in panel_list_lat_lon:
        points = panel_info['all_points']
        if len(points) >= 4:
            area_list.append(get_area_of_polygon(points))
            filtered_panel_list_lat_lon.append(panel_info)

    panel_list_lat_lon = filtered_panel_list_lat_lon
            
    # craft a new JSON
    new_json_dict = {}
    new_json_dict['image_id'] = input_json['image_id']
    new_json_dict['image_size'] = {
        "width" : input_json['image_size']['width'],
        "height" : input_json['image_size']['height']
    }
    panel_final_info_list = []
    for i in range(0, len(panel_list_lat_lon)):
        new_panel_info = {}
        
        x_points, y_points = zip(*panel_list_lat_lon[i]['all_points'])
        new_panel_info['all_points_x'] = x_points
        new_panel_info['all_points_y'] = y_points

        new_panel_info['mean_point_latitude'] = panel_list_lat_lon[i]['mean_point'][0]
        new_panel_info['mean_point_longitude'] = panel_list_lat_lon[i]['mean_point'][1]

        new_panel_info['shape_area_m2'] = area_list[i]

        panel_final_info_list.append({
            "shape_attributes" : new_panel_info
        })

    new_json_dict['panel'] = panel_final_info_list

    # save as a file
    with open(f"{output_json_dir}/{input_json['image_id']}_output.json", 'w', encoding='utf-8') as json_file:
        json.dump(new_json_dict, json_file, ensure_ascii=False, indent=4)
    
    return

def process_all_files(input_dir, metadata_dir, output_dir, image_dir):
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Iterate over all files in the input directory
    for file_name in os.listdir(input_dir):
        if file_name.endswith(".json"):
            input_json_path = os.path.join(input_dir, file_name)
            image_id = file_name.split(".json")[0]

            # Check if metadata file exists
            metadata_path = os.path.join(metadata_dir, f"{image_id}.json")
            if not os.path.exists(metadata_path):
                print(f"Metadata not found for {image_id}. Skipping.")
                continue

            # Process the file
            print(f"Processing {input_json_path}...")
            convert_xy_to_lat_lon(input_json_path, image_dir, metadata_dir, output_dir)

if __name__ == "__main__":
    input_dir = './input_json'
    metadata_dir = './metadata_json'
    output_dir = './output_data'
    image_dir = '/Volumes/T7/images'

    process_all_files(input_dir, metadata_dir, output_dir, image_dir)
