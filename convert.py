import pyproj
import math
from PIL import Image, ImageDraw

# no limit on the image size
Image.MAX_IMAGE_PIXELS = None

# mark image center with small circle
def mark_center_in_image(image_path):
    
    img = Image.open(image_path)
    width, height = img.size

    center_x = width // 2
    center_y = height // 2

    circle_radius = int(min(width, height) * 0.01)

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

    circle_radius = int(min(width, height) * 0.01)

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


if __name__ == "__main__": 
    # these values will be provided by the metadata
    ##################
    lat_0 = 38.0
    lon_0 = 127.0
    x_0 = 200000
    y_0 = 600000
    x_tm = 228580  # Easting
    y_tm = 419031  # Northing
    image_resolution = 0.11 # Indicating 1 pixel size in meter (??)
    ##################

    # test value
    ##################
    x = 3000
    y = 2000
    ##################

    # get image size
    image_width_px, image_height_px = get_image_px_info("./images/202402603C00810022.tif")

    # get center
    center_lat, center_lon = convert_GRS(lat_0, lon_0, x_0, y_0, x_tm, y_tm)

    # get origin
    origin_lat_lon = get_origin_point(center_lat, center_lon, image_width_px, image_height_px, image_resolution)

    # get (x,y)
    x_y_to_lat_lon = get_x_y(x, y, origin_lat_lon[0], origin_lat_lon[1], image_resolution)
    print(x_y_to_lat_lon)

    # debug : mark
    mark_center_in_image("./images/202402603C00810022.tif")
    mark_x_y_in_image("./images/202402603C00810022.tif", x, y)


