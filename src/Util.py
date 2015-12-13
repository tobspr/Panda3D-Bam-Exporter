

def convert_to_panda_filepath(filepath):
    """ Converts a blender filepath to a panda filepath """
    filepath = filepath.replace("\\", "/")
    if ":/" in filepath:
        idx = filepath.index(":/")
        filepath = "/" + filepath[0:idx].lower() + "/" + filepath[idx+2:]

    # Blender indicates relative paths with a double slash
    if filepath.startswith("//"):
        filepath = "./" + filepath[2:]

    return filepath

def convert_blender_file_format(extension):
    """ Converts a blender format like JPEG to an extension like .jpeg """

    extensions = {
        "BMP": ".bmp",
        "PNG": ".png",
        "JPEG": ".jpg",
        "TARGA": ".tga",
        "TIFF": ".tiff"
    }

    if extension in extensions:
        return extensions[extension]

    # In case we can't find the extension, return png
    print("Warning: Unkown blender file format:", extension)
    return ".png"

