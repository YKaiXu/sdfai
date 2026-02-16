"""
SDFAI Channel Module - 一切皆文件的通讯通道
"""
from .base import Channel, ChannelMessage, ChannelType
from .feishu import FeishuChannel
from .xunfei import XunfeiChannel
from .sdfcom import SDFComChannel

__all__ = [
    'Channel', 'ChannelMessage', 'ChannelType',
    'FeishuChannel', 'XunfeiChannel', 'SDFComChannel'
]
