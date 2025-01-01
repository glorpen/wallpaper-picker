# Wallpaper Picker

| [Codeberg](https://codeberg.org/glorpen/wallpaper-picker)
| Mirrors:
    [GitLab](https://gitlab.com/glorpen/wallpaper-picker),
    [GitHub](https://github.com/glorpen/wallpaper-picker),
    [Bitbucket](https://bitbucket.org/glorpen/wallpaper-picker)
|

Randomize your wallpaper in a smarter way.

Picker allows you to set X11 & Wayland wallpaper, picked at random from wallpaper dir.

For each image you can define POI (x,y coords) and then image will always be centered on given point - e.g. in portrait mode. 
Images will be scaled up or down to match screen resolution.

## Installation

```shell
pip install glorpen-wallpaper-picker
```

## Usage

To update wallpaper, including picking from images marked as offensive:

```
$ wallpaper-picker wallpaper --offensive
```

To change attrs:

```
$ ./.env/bin/wallpaper-picker attr-set image.jpg --offensive y --poi 1,2
Details for image /tmp/image.jpg
POI: x:1, y:2
Offensive: yes
```


To list current attributes of given file:

```
$ wallpaper-picker attr-get image.jpg
Details for image /tmp/image.jpg
POI: x:1, y:2
Offensive: yes
```

To remove attrs use `none` or `unset` as values:

```
$ wallpaper-picker attr-set image.jpg --offensive unset --poi unset
Details for image /tmp/image.jpg
POI: not set
Offensive: no
```
