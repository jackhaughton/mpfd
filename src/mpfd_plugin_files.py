'''
Created on 5 Jun 2013

@author: JSH
'''

import mpfd
import os
import threading

class MPFDFilesMetadataIndexerThread(threading.Thread):
    def __init__(self, plugin):
        self.plugin=plugin
        self.daemon=True
        self.stopping=False
        
    def stop(self):
        self.stopping=True
        
    def run(self):
        metadataPlugins=[x for x in mpfd.plugins if hasattr(x, 'getFileMetadata')]
        dbPlugin=mpfd.getDBPlugin()
        artistDict={}
        albumDict={}
        for root, dirs, files in os.walk(self.plugin.root):
            for f in files:
                for plugin in metadataPlugins:
                    md=plugin.getFileMetadata(os.path.join(root,f))
                    if md:
                        if 'artist' in md:
                            if not md['artist'] in artistDict:
                                artistDict[md['artist']]=[]
                            artistDict[md['artist']].append(md)
                        if 'album' in md:
                            if not md['album'] in albumDict:
                                albumDict[md['album']]=[]
                            albumDict[md['album']].append(md)
                        break
            if self.stopping:
                return
        dbPlugin.storeDB("filesMetadataArtists",artistDict)
        dbPlugin.storeDB("filesMetadataAlbums",albumDict)
    
class MPFDFilesMountpoint:
    def __init__(self, mp, mpType):
        self.mp=mp
        self.mpType=mpType
        
    def isDirectory(self):
        return 'directory' in self.mpType
        
class MPFDFilesPlugin:
    def __init__(self, root, mountpoints):
        self.root=root
        self.mountpoints=mountpoints
        self.filePlayerPlugins=None
        #TODO: Load metadata on a thread
        self.metadataIndexerThread=None
        self.metadataReady=False
    
    def start(self):
        if any(not x.isDirectory() for x in self.mountpoints):
            self.metadataIndexerThread=MPFDFilesMetadataIndexerThread(self)
            self.metadataIndexerThread.start()
            
    def stop(self):
        if self.metadataIndexerThread:
            self.metadataIndexerThread.stop()
    
    def getFilePlayers(self):
        self.filePlayerPlugins=[x for x in mpfd.plugins if hasattr(x, "fileFilter")]
    
    def listDirectoryMountpoint(self, subdir):
        path=os.path.join(self.root,subdir)
        entries=os.listdir(path)
        result=[]
        for entry in entries:
            if os.path.isdir(os.path.join(path,entry)):
                result.insert(0,{'name':entry, 'type': 'dir'})
            else:
                for plugin in self.filePlayerPlugins:
                    realname=plugin.fileFilter(entry)
                    if realname!=None:
                        result.append({'name':entry, 'realname': realname, 'type': 'file'})
                        break
        return result
    
    def listMetadataMountpoint(self, mountpoint, subdir):
        dbPlugin=mpfd.getDBPlugin()
        
        return [{ 'name': 'test', 'realname': 'test', 'type': 'file'}]
    
    def listDir(self, dirname):
        if self.filePlayerPlugins==None:
            self.getFilePlayers()
        result=[]
        for mountpoint in self.mountpoints:
            if dirname.startswith(mountpoint.mp):            
                subdir=dirname[len(mountpoint.mp):].strip(mpfd.path_separator)
                if mountpoint.isDirectory():
                    result.extend(self.listDirectoryMountpoint(subdir))
                else:
                    result.extend(self.listMetadataMountpoint(mountpoint,subdir))
            else:
                mpPartitioned=mountpoint.mp.rpartition(mpfd.path_separator)
                if dirname.rstrip(mpfd.path_separator)==mpPartitioned[0]:
                    result.append({'name':mpPartitioned[2], 'type': 'dir'})
        return result

mpTypes=[ 'directory', 'album', 'artist' ]
def extractMountpoint(mpStr):
    cparts=mpStr.split(',')
    mpType=[]
    while cparts[-1] in mpTypes:
        mpType.insert(0,cparts.pop())
    return MPFDFilesMountpoint(','.join(cparts),mpType)
        
def createInstance(config):
    return MPFDFilesPlugin(config['root'], [extractMountpoint(config[x]) for x in config if x.startswith("mountpoint")])