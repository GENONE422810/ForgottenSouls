class_name DecaChunkData
extends RefCounted

var coord: Vector2i = Vector2i.ZERO
var climate: ClimateProfile = ClimateProfile.new()

var is_ocean: bool = false
var terrain: int = 0

var river_sources: Array = []
var economy: Dictionary = {}
var politics: Dictionary = {}
var resources: Dictionary = {}
var history: Array = []

func to_dict() -> Dictionary:
	return {
		"coord": {"x": coord.x, "y": coord.y},
		"climate": climate.to_dict(),
		"is_ocean": is_ocean,
		"terrain": terrain,
		"river_sources": river_sources,
		"economy": economy,
		"politics": politics,
		"resources": resources,
		"history": history
	}

static func from_dict(data: Dictionary) -> DecaChunkData:
	var d := DecaChunkData.new()

	var c := data.get("coord", {"x": 0, "y": 0})
	d.coord = Vector2i(int(c.get("x", 0)), int(c.get("y", 0)))

	var climate_data: Dictionary = data.get("climate", {})
	d.climate = ClimateProfile.from_dict(climate_data)

	d.is_ocean = bool(data.get("is_ocean", false))
	d.terrain = int(data.get("terrain", 0))
	d.river_sources = data.get("river_sources", [])
	d.economy = data.get("economy", {})
	d.politics = data.get("politics", {})
	d.resources = data.get("resources", {})
	d.history = data.get("history", [])
	return d