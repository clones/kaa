# ##################################################################
# Brain Dump
#
# - Improve RSS channel for better video and audio feed support
#   https://channelguide.participatoryculture.org/front
# - Flickr image channel
# - Torrent downloader (needed for some democracy channels)
# - Add more item metadata (e.g. download thumbnail/image)
# - Channel configuration:
#   o always download / download on demand / play from stream
#   o how much entries should be show
#   o keep entries on hd (while in feed / while not watched / up to x)
# - Add parallel download function
# - Add channel as 'file' to kaa.beacon making it possible to merge
#   feed entries and real files.
#   o does it belong into beacon?
#   o is it an extra kaa module with beacon plugin?
#   o daemon to keep feeds in beacon up-to-date
#
# ##################################################################


import channel
import plugins

add_password = channel.pm.add_password
Channel = channel.get_channel
