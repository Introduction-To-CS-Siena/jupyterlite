from JES import *

def shrink(source):
  # set up target picture
  target = makeEmptyPicture( getWidth(source)//2, getHeight(source)//2)
  
  # do the actual copying
  sourceX = 0
  for targetX in range(0, getWidth(source)//2):
    sourceY = 0
    for targetY in range(0, getHeight(source)//2):
      color = getColor(getPixel(source, sourceX, sourceY))
      setColor(getPixel(target, targetX, targetY), color)
      sourceY = sourceY + 2
    sourceX = sourceX + 2
  return target    
  
def grow(source):
  # set up target picture
  target = makeEmptyPicture( getWidth(source) * 2, getHeight(source) * 2)
  
  # do the actual copying
  sourceX = 0
  for targetX in range(0, getWidth(source) * 2):
    sourceY = 0
    for targetY in range(0, getHeight(source) * 2):
      color = getColor(getPixel(source, int(sourceX), int(sourceY)))
      setColor(getPixel(target, targetX, targetY), color)
      sourceY = sourceY + 0.5
    sourceX = sourceX + 0.5
  return target    