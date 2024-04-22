# Create your views here.
import json

from bson import ObjectId
from django.http import JsonResponse
from django.views.generic.base import View

from monitor.statistics import statistics
from utils.log import logger
from utils.mongo_json import MongoJsonResponse, clean
from utils.response_code import page_get, ok, pipeline_page, ERROR
from ws.models import OnlineClient


class MonitorDocs():
    def list_doc(self):
        """
              @api {GET} api/monitor/clients monitor列表
              @apiVersion 1.0.0
              @apiName Monitor List
              @apiGroup Monitor
              @apiDescription monitor列表

              @apiParam {Number} [page] 页码，默认1
              @apiParam {Number} [limit] 每页条数，默认25

              @apiParamExample {json} Request-Example:
              // 查询条件
              {
                "machine_code": "7e204f477ea640fb91beb71daf1f2c62",
                "tags": [
                    "a",
                    "b"
                ],
                "business_group":"a",
                "asset_serial":"aaad",
                "location":"l1",
                "status": 1,
                "last_update_from": "2021-07-13 15:03:14",
                "last_update_to": "2021-07-13 15:03:14",
                "name": "LG Electronics11231",
                "agent_version":"1.0"
              }

              @apiSuccessExample Response-Success:
                  HTTP 1.1/ 200K
                  {
                    "code": 200,
                    "msg": "ok",
                    "data": {
                        "itemsPerPage": 25,
                        "totalItems": 1,
                        "totalPages": 1,
                        "data": [
                            {
                                "_id": "60ed599cbb9f203cd0c80c66",
                                "online_time": "2021-07-13 17:15:08",
                                "client": [
                                    "172.20.0.10",
                                    43794
                                ],
                                "machine_code": "7e204f477ea640fb91beb71daf1f2c62",
                                "tags": [],
                                "status": 0,
                                "last_update": "2021-07-13 17:15:09",
                                "name": "LG Electronics17Z90N-V.AA76C (version: 0.1)"
                            }
                        ]
                    }
                }
        """

    def detail_doc(self):
        """
              @api {GET} api/monitor/clients/:id monitor详情
              @apiVersion 1.0.0
              @apiName Monitor Detail
              @apiGroup Monitor
              @apiDescription monitor详情

              @apiParam {String} id monitorId

              @apiSuccessExample Response-Success:
                  HTTP 1.1/ 200K
                  {
                    "code": 200,
                    "msg": "ok",
                    "data": {
                        "_id": "60ed3ac66008115e051cbae8",
                        "name": "LG Electronics11231",
                        "groups": [],
                        "is_anonymous": 0,
                        "online_time": "2021-07-13 15:03:34",
                        "client": [
                            "127.0.0.1",
                            43520
                        ],
                        "machine_code": "7e204f477ea640fb91beb71daf1f2c62",
                        "tags": [
                            "a",
                            "b"
                        ],
                        "client_info": {
                            "manufacturer": "LG Electronics",
                            "model": "17Z90N-V.AA76C (version: 0.1)",
                            "serialNumber": "unknown",
                            "firmware": {
                                "manufacturer": "Phoenix Technologies Ltd.",
                                "name": "unknown",
                                "version": "C2ZE0160 X64",
                                "description": "dmi:bvnPhoenixTechnologiesLtd.:bvrC2ZE0160X64:bd04/07/2020:svnLGElectronics:pn17Z90N-V.AA76C:pvr0.1:rvnLGElectronics:rn17Z90N:rvrFAB1:cvnLGElectronics:ct10:cvr0.1:",
                                "releaseDate": "04/07/2020"
                            },
                            "baseboard": {
                                "manufacturer": "LG Electronics",
                                "model": "17Z90N",
                                "version": "FAB1",
                                "serialNumber": ""
                            },
                            "central_processor": {
                                "physicalProcessorCount": 4,
                                "logicalProcessorCount": 8,
                                "identifier": "Intel64 Family 6 Model 126 Stepping 5",
                                "processorId": "AFC1FBFF007006E5"
                            },
                            "memory": {
                                "available": "2.8 GiB",
                                "total": "15.3 GiB",
                                "swapUsed": "50.8 MiB",
                                "swapTotal": "7.6 GiB"
                            },
                            "operate_system": {
                                "family": "Ubuntu",
                                "manufacturer": "GNU/Linux",
                                "version": "18.04.5 LTS",
                                "codeName": "Bionic Beaver",
                                "buildNumber": "5.4.0-77-generic"
                            },
                            "network_info": {
                                "hostname": "ran",
                                "domainName": "ran",
                                "dnsServers": [
                                    "127.0.0.53"
                                ],
                                "ipv4DefaultGateway": "",
                                "ipv6DefaultGateway": "",
                                "networkInterfaces": [
                                    {
                                        "name": "vetha2382b4",
                                        "displayName": "vetha2382b4",
                                        "mtu": 1500,
                                        "speed": "10 Kbps",
                                        "ipv4addr": [],
                                        "ipv6addr": [
                                            "fe80:0:0:0:f046:3eff:fec5:a28b"
                                        ],
                                        "bytesRecv": 41403,
                                        "bytesSent": 37530,
                                        "packetRecv": 187,
                                        "packetSent": 328
                                    },
                                    {
                                        "name": "wlp0s20f3",
                                        "displayName": "wlp0s20f3",
                                        "mtu": 1500,
                                        "speed": "0 bps",
                                        "ipv4addr": [],
                                        "ipv6addr": [
                                            "fe80:0:0:0:e25e:f6bd:f73e:1ddd"
                                        ],
                                        "bytesRecv": 497491234,
                                        "bytesSent": 11490667,
                                        "packetRecv": 1580620,
                                        "packetSent": 100911
                                    },
                                    {
                                        "name": "br-353b43be29e6",
                                        "displayName": "br-353b43be29e6",
                                        "mtu": 1500,
                                        "speed": "0 bps",
                                        "ipv4addr": [
                                            "172.20.0.1"
                                        ],
                                        "ipv6addr": [],
                                        "bytesRecv": 0,
                                        "bytesSent": 0,
                                        "packetRecv": 0,
                                        "packetSent": 0
                                    },
                                    {
                                        "name": "br-0b09da011efe",
                                        "displayName": "br-0b09da011efe",
                                        "mtu": 1500,
                                        "speed": "0 bps",
                                        "ipv4addr": [
                                            "172.22.0.1"
                                        ],
                                        "ipv6addr": [],
                                        "bytesRecv": 0,
                                        "bytesSent": 0,
                                        "packetRecv": 0,
                                        "packetSent": 0
                                    },
                                    {
                                        "name": "br-f965f953a2fc",
                                        "displayName": "br-f965f953a2fc",
                                        "mtu": 1500,
                                        "speed": "0 bps",
                                        "ipv4addr": [
                                            "172.19.0.1"
                                        ],
                                        "ipv6addr": [],
                                        "bytesRecv": 0,
                                        "bytesSent": 0,
                                        "packetRecv": 0,
                                        "packetSent": 0
                                    },
                                    {
                                        "name": "br-c4c353042006",
                                        "displayName": "br-c4c353042006",
                                        "mtu": 1500,
                                        "speed": "0 bps",
                                        "ipv4addr": [
                                            "172.21.0.1"
                                        ],
                                        "ipv6addr": [],
                                        "bytesRecv": 0,
                                        "bytesSent": 0,
                                        "packetRecv": 0,
                                        "packetSent": 0
                                    },
                                    {
                                        "name": "br-be80dc44a878",
                                        "displayName": "br-be80dc44a878",
                                        "mtu": 1500,
                                        "speed": "0 bps",
                                        "ipv4addr": [
                                            "172.23.0.1"
                                        ],
                                        "ipv6addr": [
                                            "fe80:0:0:0:42:12ff:fef1:3bb1"
                                        ],
                                        "bytesRecv": 38785,
                                        "bytesSent": 33560,
                                        "packetRecv": 187,
                                        "packetSent": 292
                                    },
                                    {
                                        "name": "br-5fe262296f0d",
                                        "displayName": "br-5fe262296f0d",
                                        "mtu": 1500,
                                        "speed": "0 bps",
                                        "ipv4addr": [
                                            "172.24.0.1"
                                        ],
                                        "ipv6addr": [],
                                        "bytesRecv": 0,
                                        "bytesSent": 0,
                                        "packetRecv": 0,
                                        "packetSent": 0
                                    },
                                    {
                                        "name": "docker0",
                                        "displayName": "docker0",
                                        "mtu": 1500,
                                        "speed": "0 bps",
                                        "ipv4addr": [
                                            "172.17.0.1"
                                        ],
                                        "ipv6addr": [],
                                        "bytesRecv": 0,
                                        "bytesSent": 0,
                                        "packetRecv": 0,
                                        "packetSent": 0
                                    },
                                    {
                                        "name": "br-4e9c057d8785",
                                        "displayName": "br-4e9c057d8785",
                                        "mtu": 1500,
                                        "speed": "0 bps",
                                        "ipv4addr": [
                                            "172.18.0.1"
                                        ],
                                        "ipv6addr": [],
                                        "bytesRecv": 0,
                                        "bytesSent": 0,
                                        "packetRecv": 0,
                                        "packetSent": 0
                                    }
                                ]
                            },
                            "filesystem_info": {
                                "total": "292.2 GiB",
                                "usable": "35.8 GiB",
                                "totalBytes": 313706622976,
                                "usableBytes": 38430334976,
                                "fileSystem": [
                                    {
                                        "name": "/",
                                        "type": "ext4",
                                        "usable": "16.6 GiB",
                                        "usableBytes": 17868337152,
                                        "totalSpace": "130.4 GiB",
                                        "totalSpaceBytes": 140034801664,
                                        "freePercentage": "12.759926061004",
                                        "volume": "/dev/nvme0n1p10",
                                        "logicalVolume": "",
                                        "mount": "/"
                                    },
                                    {
                                        "name": "/dev/loop2",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "57.3 MiB",
                                        "totalSpaceBytes": 60030976,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop2",
                                        "logicalVolume": "",
                                        "mount": "/snap/sublime-text/97"
                                    },
                                    {
                                        "name": "/dev/loop4",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "640 KiB",
                                        "totalSpaceBytes": 655360,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop4",
                                        "logicalVolume": "",
                                        "mount": "/snap/gnome-logs/103"
                                    },
                                    {
                                        "name": "/dev/loop3",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "2.5 MiB",
                                        "totalSpaceBytes": 2621440,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop3",
                                        "logicalVolume": "",
                                        "mount": "/snap/gnome-system-monitor/160"
                                    },
                                    {
                                        "name": "/dev/loop5",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "55.5 MiB",
                                        "totalSpaceBytes": 58195968,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop5",
                                        "logicalVolume": "",
                                        "mount": "/snap/core18/2074"
                                    },
                                    {
                                        "name": "/dev/loop1",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "768 KiB",
                                        "totalSpaceBytes": 786432,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop1",
                                        "logicalVolume": "",
                                        "mount": "/snap/gnome-characters/726"
                                    },
                                    {
                                        "name": "/dev/loop6",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "219 MiB",
                                        "totalSpaceBytes": 229638144,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop6",
                                        "logicalVolume": "",
                                        "mount": "/snap/gnome-3-34-1804/66"
                                    },
                                    {
                                        "name": "/dev/loop7",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "55.5 MiB",
                                        "totalSpaceBytes": 58195968,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop7",
                                        "logicalVolume": "",
                                        "mount": "/snap/core18/2066"
                                    },
                                    {
                                        "name": "/dev/nvme0n1p1",
                                        "type": "vfat",
                                        "usable": "205.4 MiB",
                                        "usableBytes": 215384064,
                                        "totalSpace": "256 MiB",
                                        "totalSpaceBytes": 268435456,
                                        "freePercentage": "80.23681640625",
                                        "volume": "/dev/nvme0n1p1",
                                        "logicalVolume": "",
                                        "mount": "/boot/efi"
                                    },
                                    {
                                        "name": "/dev/loop0",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "110.8 MiB",
                                        "totalSpaceBytes": 116129792,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop0",
                                        "logicalVolume": "",
                                        "mount": "/snap/qv2ray/4576"
                                    },
                                    {
                                        "name": "/dev/loop8",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "244 MiB",
                                        "totalSpaceBytes": 255852544,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop8",
                                        "logicalVolume": "",
                                        "mount": "/snap/gnome-3-38-2004/39"
                                    },
                                    {
                                        "name": "/dev/loop10",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "64.9 MiB",
                                        "totalSpaceBytes": 68026368,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop10",
                                        "logicalVolume": "",
                                        "mount": "/snap/gtk-common-themes/1514"
                                    },
                                    {
                                        "name": "/dev/loop12",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "301.5 MiB",
                                        "totalSpaceBytes": 316145664,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop12",
                                        "logicalVolume": "",
                                        "mount": "/snap/telegram-desktop/2831"
                                    },
                                    {
                                        "name": "/dev/loop9",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "219 MiB",
                                        "totalSpaceBytes": 229638144,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop9",
                                        "logicalVolume": "",
                                        "mount": "/snap/gnome-3-34-1804/72"
                                    },
                                    {
                                        "name": "/dev/loop11",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "61.8 MiB",
                                        "totalSpaceBytes": 64749568,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop11",
                                        "logicalVolume": "",
                                        "mount": "/snap/core20/975"
                                    },
                                    {
                                        "name": "/dev/loop13",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "768 KiB",
                                        "totalSpaceBytes": 786432,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop13",
                                        "logicalVolume": "",
                                        "mount": "/snap/gnome-characters/723"
                                    },
                                    {
                                        "name": "/dev/loop14",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "301.5 MiB",
                                        "totalSpaceBytes": 316145664,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop14",
                                        "logicalVolume": "",
                                        "mount": "/snap/telegram-desktop/2841"
                                    },
                                    {
                                        "name": "/dev/nvme0n1p11",
                                        "type": "ext4",
                                        "usable": "2.2 GiB",
                                        "usableBytes": 2411167744,
                                        "totalSpace": "28.1 GiB",
                                        "totalSpaceBytes": 30165315584,
                                        "freePercentage": "7.993179243511408",
                                        "volume": "/dev/nvme0n1p11",
                                        "logicalVolume": "",
                                        "mount": "/home"
                                    },
                                    {
                                        "name": "/dev/loop15",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "1.6 MiB",
                                        "totalSpaceBytes": 1703936,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop15",
                                        "logicalVolume": "",
                                        "mount": "/snap/scc/16"
                                    },
                                    {
                                        "name": "/dev/loop16",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "2.5 MiB",
                                        "totalSpaceBytes": 2621440,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop16",
                                        "logicalVolume": "",
                                        "mount": "/snap/gnome-calculator/826"
                                    },
                                    {
                                        "name": "/dev/loop17",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "50.5 MiB",
                                        "totalSpaceBytes": 52953088,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop17",
                                        "logicalVolume": "",
                                        "mount": "/snap/sublime-text/102"
                                    },
                                    {
                                        "name": "/dev/loop18",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "191.9 MiB",
                                        "totalSpaceBytes": 201195520,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop18",
                                        "logicalVolume": "",
                                        "mount": "/snap/mailspring/502"
                                    },
                                    {
                                        "name": "/dev/loop19",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "175.4 MiB",
                                        "totalSpaceBytes": 183894016,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop19",
                                        "logicalVolume": "",
                                        "mount": "/snap/postman/133"
                                    },
                                    {
                                        "name": "/dev/loop20",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "110.8 MiB",
                                        "totalSpaceBytes": 116129792,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop20",
                                        "logicalVolume": "",
                                        "mount": "/snap/qv2ray/4531"
                                    },
                                    {
                                        "name": "/dev/loop21",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "65.1 MiB",
                                        "totalSpaceBytes": 68288512,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop21",
                                        "logicalVolume": "",
                                        "mount": "/snap/gtk-common-themes/1515"
                                    },
                                    {
                                        "name": "/dev/loop22",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "32.4 MiB",
                                        "totalSpaceBytes": 33947648,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop22",
                                        "logicalVolume": "",
                                        "mount": "/snap/snapd/12398"
                                    },
                                    {
                                        "name": "/dev/loop23",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "61.8 MiB",
                                        "totalSpaceBytes": 64749568,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop23",
                                        "logicalVolume": "",
                                        "mount": "/snap/core20/1026"
                                    },
                                    {
                                        "name": "/dev/loop24",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "32.4 MiB",
                                        "totalSpaceBytes": 33947648,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop24",
                                        "logicalVolume": "",
                                        "mount": "/snap/snapd/12159"
                                    },
                                    {
                                        "name": "/dev/loop25",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "2.5 MiB",
                                        "totalSpaceBytes": 2621440,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop25",
                                        "logicalVolume": "",
                                        "mount": "/snap/gnome-system-monitor/163"
                                    },
                                    {
                                        "name": "/dev/loop26",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "191.6 MiB",
                                        "totalSpaceBytes": 200933376,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop26",
                                        "logicalVolume": "",
                                        "mount": "/snap/mailspring/505"
                                    },
                                    {
                                        "name": "/dev/loop27",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "175.4 MiB",
                                        "totalSpaceBytes": 183894016,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop27",
                                        "logicalVolume": "",
                                        "mount": "/snap/postman/132"
                                    },
                                    {
                                        "name": "/dev/loop28",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "99.4 MiB",
                                        "totalSpaceBytes": 104202240,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop28",
                                        "logicalVolume": "",
                                        "mount": "/snap/core/11187"
                                    },
                                    {
                                        "name": "/dev/loop29",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "99.4 MiB",
                                        "totalSpaceBytes": 104202240,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop29",
                                        "logicalVolume": "",
                                        "mount": "/snap/core/11316"
                                    },
                                    {
                                        "name": "/dev/loop30",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "2.5 MiB",
                                        "totalSpaceBytes": 2621440,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop30",
                                        "logicalVolume": "",
                                        "mount": "/snap/gnome-calculator/884"
                                    },
                                    {
                                        "name": "/dev/loop31",
                                        "type": "squashfs",
                                        "usable": "0 bytes",
                                        "usableBytes": 0,
                                        "totalSpace": "640 KiB",
                                        "totalSpaceBytes": 655360,
                                        "freePercentage": "0.0",
                                        "volume": "/dev/loop31",
                                        "logicalVolume": "",
                                        "mount": "/snap/gnome-logs/106"
                                    },
                                    {
                                        "name": "overlay",
                                        "type": "overlay",
                                        "usable": "16.6 GiB",
                                        "usableBytes": 17868337152,
                                        "totalSpace": "130.4 GiB",
                                        "totalSpaceBytes": 140034801664,
                                        "freePercentage": "12.759926061004",
                                        "volume": "overlay",
                                        "logicalVolume": "",
                                        "mount": "/var/lib/docker/overlay2/4cbf41904518ec2ec08baf9c16c66ea40e08a9fe66f07cbff3bc119a5a835639/merged"
                                    },
                                    {
                                        "name": "shm",
                                        "type": "tmpfs",
                                        "usable": "64 MiB",
                                        "usableBytes": 67108864,
                                        "totalSpace": "64 MiB",
                                        "totalSpaceBytes": 67108864,
                                        "freePercentage": "100.0",
                                        "volume": "shm",
                                        "logicalVolume": "",
                                        "mount": "/var/lib/docker/containers/4136de0297bbc753a828cf3bcd21e71bf865d87ad906b4a7dc951d920f2c8664/mounts/shm"
                                    }
                                ]
                            }
                        },
                        "status": 1,
                        "last_update": "2021-07-13 15:04:14"
                    }
                }
        """

    def put_doc(self):
        """
             @api {PUT} api/monitor/clients/:id monitor更新
             @apiVersion 1.0.0
             @apiName Monitor Put
             @apiGroup Monitor
             @apiDescription 修改monitor

             @apiParam {String} id monitorId

             @apiParamExample {json} Request-Example:
             {
                "machine_code": "7e204f477ea640fb91beb71daf1f2c62",
                "tags": [
                    "a",
                    "b"
                ],
                "business_group": "a",
                "asset_serial": "aaad",
                "location": "l1",
                "status": 1,
                "last_update": "2021-07-13 15:04:14",
                "name": "LG Electronics11231",
                "agent_version": "1.0"
            }

             @apiSuccessExample Response-Success:
                 HTTP 1.1/ 200K
                 {                                                                              
                    "code": 200,
                    "msg": "ok",
                    "data": null
                }
       """


class MonitorView(View):
    list_exclude = ('groups', 'single_group', 'channel_name', 'channel_layer_alias',
                    'is_anonymous', 'is_random_gen', 'client_info')

    def get(self, request):
        query_dict = request.REQUEST
        page, per_page = page_get(request.GET)
        pipeline = [OnlineClient.pre_match(query_dict), {'skip'}, {'limit'},
                    OnlineClient.projects(self.__class__.list_exclude, is_include=0)]
        logger.info(pipeline)
        return MongoJsonResponse(ok(pipeline_page(OnlineClient, pipeline, page, per_page)))


class MonitorDetailView(View):
    detail_exclude = ('groups', 'single_group', 'channel_name', 'channel_layer_alias',
                      'is_anonymous', 'is_random_gen')

    def get(self, request, id):
        client = OnlineClient.objects(id=ObjectId(id)).exclude(*self.__class__.detail_exclude).first()
        if client is None:
            return JsonResponse(ERROR.NOT_FOUND_404)
        return MongoJsonResponse(ok(client))

    def post(self, request):
        return JsonResponse(ok())

    def put(self, request, id):
        doc = OnlineClient.objects(id=id).first()
        if doc is None:
            return JsonResponse(ERROR.NOT_FOUND_404)

        data_dict = clean(request.REQUEST, OnlineClient.only_fields())
        data_json = json.dumps(data_dict)
        client = OnlineClient.from_json(data_json)

        obj_list = dir(doc)
        for k in data_dict.keys():
            if k in obj_list and k not in self.detail_exclude:
                setattr(doc, k, getattr(client, k))
        doc.save()
        return MongoJsonResponse(ok())


class StatisticsView(View):

    def get(self, request):
        """
        @api {GET} api/monitor/statistics 大屏统计
        @apiVersion 1.0.0
        @apiName statistics
        @apiGroup Statistics
        @apiDescription 大屏统计

        @apiSuccessExample Response-Success:
            HTTP 1.1/ 200K
        {
            "code": 200,
            "msg": "ok",
            "data": {
                "client_statistic": { // 客户端统计
                    "client_count": 4, //节点数量
                    "online_client_count": 2 // 在线节点数量
                },
                "weakness_audit_statistic": { // 缺陷、审计统计
                    "_id": null,
                    "weakness_count": 6, // 总缺陷数量
                    "audit_count": 4 // 已审计数量
                },
                "category_weakness_statistic": [// 类别分组统计
                    {
                        "category": "安全功能", // 类别名称
                        "count": 38, // 缺陷数量
                        "audit": 5 // 已审计数量
                    }
                ],
                "rule_weakness_statistic": [ // 规则分组统计
                    {
                        "rule": "远端命令注入",
                        "count": 2,
                        "audit": 1
                    },
                    {
                        "rule": "远端命令注入1",
                        "count": 3,
                        "audit": 0
                    },
                    {
                        "rule": "远端命令注入2",
                        "count": 3,
                        "audit": 0
                    },
                    {
                        "rule": "远端命令注入1",
                        "count": 14,
                        "audit": 0
                    },
                    {
                        "rule": "远端命令注入2",
                        "count": 7,
                        "audit": 0
                    },
                    {
                        "rule": "命令注入",
                        "count": 9,
                        "audit": 4
                    }
                ],
                "level_weakness_statistic": [// 等级分组统计
                    {
                        "level": 1, // level，1,低，2，中，3,高
                        "count": 38,
                        "audit": 5
                    }
                ],
                "project_statistic": { //项目统计
                    "_id": null,
                    "count": 6 // 项目数量
                }
            }
        }
        """
        return MongoJsonResponse(ok(statistics()))
