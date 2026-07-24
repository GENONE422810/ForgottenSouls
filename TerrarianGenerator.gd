class_name TerrainGenerator
extends RefCounted

static func biome_to_name(biome: int) -> String:
	match biome:
		BiomeData.Biome.OCEAN:
			return "ocean"
		BiomeData.Biome.BEACH:
			return "beach"
		BiomeData.Biome.PLAINS:
			return "plains"
		BiomeData.Biome.FOREST:
			return "forest"
		BiomeData.Biome.DENSE_FOREST:
			return "dense_forest"
		BiomeData.Biome.SWAMP:
			return "swamp"
		BiomeData.Biome.DESERT:
			return "desert"
		BiomeData.Biome.SAVANNA:
			return "savanna"
		BiomeData.Biome.STEPPE:
			return "steppe"
		BiomeData.Biome.TAIGA:
			return "taiga"
		BiomeData.Biome.SNOW:
			return "snow"
		BiomeData.Biome.MOUNTAIN:
			return "mountain"
		BiomeData.Biome.HIGH_MOUNTAIN:
			return "high_mountain"
		BiomeData.Biome.RIVER:
			return "river"
		_:
			return "plains"

static func name_to_biome(name: String) -> int:
	match name:
		"ocean":
			return BiomeData.Biome.OCEAN
		"beach":
			return BiomeData.Biome.BEACH
		"plains":
			return BiomeData.Biome.PLAINS
		"forest":
			return BiomeData.Biome.FOREST
		"dense_forest":
			return BiomeData.Biome.DENSE_FOREST
		"swamp":
			return BiomeData.Biome.SWAMP
		"desert":
			return BiomeData.Biome.DESERT
		"savanna":
			return BiomeData.Biome.SAVANNA
		"steppe":
			return BiomeData.Biome.STEPPE
		"taiga":
			return BiomeData.Biome.TAIGA
		"snow":
			return BiomeData.Biome.SNOW
		"mountain":
			return BiomeData.Biome.MOUNTAIN
		"high_mountain":
			return BiomeData.Biome.HIGH_MOUNTAIN
		"river":
			return BiomeData.Biome.RIVER
		_:
			return BiomeData.Biome.PLAINS

static func choose_region_terrain(profile: ClimateProfile, ocean: bool = false) -> int:
	if ocean:
		return BiomeData.Biome.OCEAN

	var h := profile.average_height
	var t := profile.average_temperature
	var m := profile.average_moisture
	var r := profile.rainfall

	if h > 0.78:
		return BiomeData.Biome.HIGH_MOUNTAIN
	if h > 0.60:
		return BiomeData.Biome.MOUNTAIN

	if h < -0.30:
		return BiomeData.Biome.BEACH

	if t < -0.65:
		if m > 0.35:
			return BiomeData.Biome.TAIGA
		return BiomeData.Biome.SNOW

	if t > 0.72:
		if m < -0.25:
			return BiomeData.Biome.DESERT
		if m < 0.15:
			return BiomeData.Biome.SAVANNA
		return BiomeData.Biome.DENSE_FOREST

	if r > 0.80 and h < 0.18:
		return BiomeData.Biome.SWAMP

	if m > 0.60:
		return BiomeData.Biome.DENSE_FOREST
	if m > 0.30:
		return BiomeData.Biome.FOREST
	if m < -0.35:
		return BiomeData.Biome.STEPPE

	return BiomeData.Biome.PLAINS

static func choose_tile_biome(
	profile: ClimateProfile,
	region_terrain: int,
	height: float,
	moisture: float,
	coast: float,
	neighbor_profile: ClimateProfile = null,
	local_pos: Vector2i = Vector2i.ZERO
) -> int:
	var temp := profile.average_temperature
	var rain := profile.rainfall
	var local_moisture := moisture

	if neighbor_profile != null:
		temp = lerp(temp, neighbor_profile.average_temperature, 0.18)
		local_moisture = lerp(local_moisture, neighbor_profile.average_moisture, 0.18)
		rain = lerp(rain, neighbor_profile.rainfall, 0.16)

	var edge := _edge_strength(local_pos)

	if coast > 0.70:
		if height <= 0.0 or region_terrain == BiomeData.Biome.OCEAN:
			return BiomeData.Biome.OCEAN
		if height < 0.05 or edge > 0.72:
			return BiomeData.Biome.BEACH
		if rain > 0.70 and height < 0.18:
			return BiomeData.Biome.SWAMP

	if height > 0.82:
		return BiomeData.Biome.HIGH_MOUNTAIN
	if height > 0.64:
		return BiomeData.Biome.MOUNTAIN

	if temp < -0.70:
		if local_moisture > 0.30:
			return BiomeData.Biome.TAIGA
		return BiomeData.Biome.SNOW

	if temp < -0.40:
		if local_moisture > 0.20:
			return BiomeData.Biome.TAIGA
		return BiomeData.Biome.SNOW

	if temp > 0.75:
		if local_moisture < -0.25:
			return BiomeData.Biome.DESERT
		if local_moisture < 0.15:
			return BiomeData.Biome.SAVANNA
		return BiomeData.Biome.DENSE_FOREST

	if rain > 0.80 and height < 0.15:
		return BiomeData.Biome.SWAMP

	if local_moisture > 0.65:
		return BiomeData.Biome.DENSE_FOREST
	if local_moisture > 0.35:
		return BiomeData.Biome.FOREST
	if local_moisture < -0.40:
		if temp > 0.50:
			return BiomeData.Biome.DESERT
		if temp > 0.15:
			return BiomeData.Biome.STEPPE
		return BiomeData.Biome.SNOW
	if local_moisture < -0.12:
		return BiomeData.Biome.STEPPE

	match region_terrain:
		BiomeData.Biome.DESERT:
			return BiomeData.Biome.DESERT
		BiomeData.Biome.SAVANNA:
			return BiomeData.Biome.SAVANNA
		BiomeData.Biome.TAIGA:
			return BiomeData.Biome.TAIGA
		BiomeData.Biome.SNOW:
			return BiomeData.Biome.SNOW
		BiomeData.Biome.FOREST:
			return BiomeData.Biome.FOREST
		BiomeData.Biome.DENSE_FOREST:
			return BiomeData.Biome.DENSE_FOREST
		BiomeData.Biome.SWAMP:
			return BiomeData.Biome.SWAMP
		_:
			return BiomeData.Biome.PLAINS

static func _edge_strength(local_pos: Vector2i) -> float:
	var edge_dist := min(
		min(local_pos.x, ChunkData.SIZE - 1 - local_pos.x),
		min(local_pos.y, ChunkData.SIZE - 1 - local_pos.y)
	)
	return 1.0 - clamp(float(edge_dist) / 4.0, 0.0, 1.0)