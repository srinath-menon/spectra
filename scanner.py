import os
import shutil
import urllib.parse

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
FAV_FOLDER = "_fav_"

def scan_disk(base_dir, target_folder=None):
    images = []
    is_all = (target_folder is None or target_folder == '.')
    
    for root, dirs, files in os.walk(base_dir):
        if is_all and FAV_FOLDER in root:
            continue
            
        if not is_all:
            rel_root = os.path.relpath(root, base_dir)
            if rel_root != target_folder:
                continue

        for file in files:
            if os.path.splitext(file)[1].lower() in EXTENSIONS:
                full_path = os.path.join(root, file)
                # Ensure the web path is relative to the base_dir
                rel_path = os.path.relpath(full_path, base_dir)
                images.append({
                    "src": urllib.parse.quote(rel_path),
                    "folder": os.path.dirname(rel_path).replace("\\", "/") 
                })
        
        if not is_all and images:
            break

    images.sort(key=lambda x: os.path.getmtime(urllib.parse.unquote(os.path.join(base_dir, x['src']))), reverse=True)
    return images

def move_to_favorites(relative_path, base_dir):
    source_path = os.path.join(base_dir, urllib.parse.unquote(relative_path))
    fav_dir = os.path.join(base_dir, FAV_FOLDER)
    
    if not os.path.exists(fav_dir):
        os.makedirs(fav_dir)
        
    filename = os.path.basename(source_path)
    destination = os.path.join(fav_dir, filename)
    shutil.move(source_path, destination)
    return True


def move_batch_to_favorites(paths_list, base_dir):
    """Moves a list of relative paths to the _fav_ folder."""
    fav_dir = os.path.join(base_dir, FAV_FOLDER)
    if not os.path.exists(fav_dir):
        os.makedirs(fav_dir)
        
    for rel_path in paths_list:
        source_path = os.path.join(base_dir, urllib.parse.unquote(rel_path))
        if os.path.exists(source_path):
            destination = os.path.join(fav_dir, os.path.basename(source_path))
            shutil.move(source_path, destination)
    return True