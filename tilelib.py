from numpy import *
from PIL import Image
import mypaintlib, helpers

tilesize = N = mypaintlib.TILE_SIZE

class Tile:
    def __init__(self):
        # note: pixels are stored with premultiplied alpha
        self.rgb   = zeros((N, N, 3), 'float32')
        self.alpha = zeros((N, N, 1), 'float32')
        self.changes = 0
        
    def compositeOverRGB8(self, dst):
        dst[:,:,0:3] *= 1.0-self.alpha # <-- isn't a 255 missing here anywawy?
        dst[:,:,0:3] += 255*self.rgb[:,:,0:3]

    def compositeOverWhiteRGB8(self, dst):
		# FIXME: to be removed; composite in high resolution
        # we are converting from linear RGB to sRGB (not precisely, but hopefully good enough)
        # FIXME: this calculation does not work with premultiplied alpha!!!?!
        #        must composite in linear space anyway!
        #dst[:,:,0:3] += 255*(self.rgb[:,:,0:3]**(1/2.2))
        def lin2srgb(x):
            return x**(1/2.2)
        dst[:,:,0:3] = 255*lin2srgb(1.0-self.alpha + self.rgb[:,:,0:3])
        # FIXME: this composites over white now...

    #def composite(self, other):
        # resultColor = topColor + (1.0 - topAlpha) * bottomColor
    #    self.rgb = other.alpha * other.rgb + (1.0-other.alpha) * self.rgb
    #    self.alpha = other.alpha + (1.0-other.alpha)*self.alpha

transparentTile = Tile()

def get_tiles_bbox(tiledict):
    res = helpers.Rect()
    for x, y in tiledict:
        res.expandToIncludeRect(helpers.Rect(N*x, N*y, N, N))
    return res

class TiledSurface(mypaintlib.TiledSurface):
    # the C++ half of this class is in tilelib.hpp
    def __init__(self):
        mypaintlib.TiledSurface.__init__(self, self)
        self.tiledict = {}
        self.alpha = 1.0
        self.observers = []

    def notify_observers(self, *args):
        for f in self.observers:
            f(*args)

    def clear(self):
        tiles = self.tiledict.keys()
        self.tiledict = {}
        for f in self.observers:
            f(*get_tiles_bbox(tiles))

    def get_tile_memory(self, x, y, readonly):
        t = self.tiledict.get((x, y))
        if t is None:
            if readonly:
                t = transparentTile
            else:
                t = Tile()
                self.tiledict[(x, y)] = t
        return t.rgb, t.alpha
        
    #def tiles(self, x, y, w, h):
    #    for xx in xrange(x/Tile.N, (x+w)/Tile.N+1):
    #        for yy in xrange(y/Tile.N, (x+h)/Tile.N+1):
    #            tile = self.tiledict.get((xx, yy), None)
    #            if tile is not None:
    #                yield xx*Tile.N, yy*Tile.N, tile

    def compositeOverRGB8(self, dst):
        h, w, channels = dst.shape
        assert channels == 3

        for (x0, y0), tile in self.tiledict.iteritems():
            x0 = N*x0
            y0 = N*y0
            if x0 < 0 or y0 < 0: continue
            if x0+N > w or y0+N > h: continue
            tile.compositeOverRGB8(dst[y0:y0+N,x0:x0+N,:])

    def compositeOverWhiteRGB8(self, dst):
        # FIXME: code duplication
        h, w, channels = dst.shape
        assert channels == 3

        for (x0, y0), tile in self.tiledict.iteritems():
            x0 = N*x0
            y0 = N*y0
            if x0 < 0 or y0 < 0: continue
            if x0+N > w or y0+N > h: continue
            tile.compositeOverWhiteRGB8(dst[y0:y0+N,x0:x0+N,:])

    def save(self, filename):
        assert self.tiledict, 'cannot save empty surface'
        a = array([xy for xy, tile in self.tiledict.iteritems()])
        minx, miny = N*a.min(0)
        sizex, sizey = N*(a.max(0) - a.min(0) + 1)
        buf = zeros((sizey, sizex, 4), 'float32')

        for (x0, y0), tile in self.tiledict.iteritems():
            x0 = N*x0 - minx
            y0 = N*y0 - miny
            dst = buf[y0:y0+N,x0:x0+N,:]
            # un-premultiply alpha
            dst[:,:,0:3] = tile.rgb[:,:,0:3] / clip(tile.alpha, 0.000001, 1.0)
            dst[:,:,3:4] = tile.alpha

        # TODO: convert to sRGB?
        buf = (buf*255).round().astype('uint8')
        im = Image.fromstring('RGBA', (sizex, sizey), buf.tostring())
        im.save(filename)

    def save_snapshot(self):
        print 'TODO: save_snapshot'
        return 'blub'
    def load_snapshot(self, data):
        print 'TODO: load_snapshot'

    def set_from_pixbuf(self, pixbuf):
        print 'TODO: set_from_pixbuf or alternative'