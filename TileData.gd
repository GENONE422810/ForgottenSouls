class_name TileData
extends RefCounted

## ID тайла в атласе
var atlas:int = 0

## Высота (для будущих скал)
var height:float = 0.0

## Дополнительные флаги
var flags:int = 0

func to_dict()->Dictionary:
	return {
		"a":atlas,
		"h":height,
		"f":flags
	}

static func from_dict(d:Dictionary)->TileData:
	var t:=TileData.new()

	t.atlas=d.get("a",0)
	t.height=d.get("h",0.0)
	t.flags=d.get("f",0)

	return t