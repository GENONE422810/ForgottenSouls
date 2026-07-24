class_name DecaChunkGenerator
extends RefCounted

static func generate(coord: Vector2i, graph: WorldGraph = null) -> DecaChunkData:
	var d := DecaChunkData.new()
	d.coord = coord

	var p := ClimateProfile.new()
	var pos := Vector2(coord) * float(ChunkData.SIZE * 10)

	var continent := WorldSeed.continent(pos)
	var height := WorldSeed.height(pos)
	var moisture := WorldSeed.moisture(pos)
	var climate := WorldSeed.climate(pos)

	height += continent * 0.85

	p.average_height = height
	p.average_moisture = moisture
	p.latitude = clamp(abs(pos.y) / 120000.0, 0.0, 1.0)
	p.average_temperature = climate - p.latitude - height * 0.35
	p.wind_strength = clamp(0.35 + p.latitude * 0.65 + (1.0 - abs(moisture)) * 0.10, 0.0, 1.0)
	p.wind_direction = Vector2.RIGHT.rotated((p.latitude - 0.5) * PI * 1.5)
	p.rainfall = clamp((moisture + 1.0) * 0.5 * 0.75 + (1.0 - abs(height)) * 0.20, 0.0, 1.0)
	p.tectonic_activity = clamp(max(0.0, height) * 0.9 + max(0.0, continent), 0.0, 1.0)

	if graph != null:
		var neighbor := graph.get_neighbor_average_profile(coord)
		if neighbor != null:
			p.average_temperature = lerp(p.average_temperature, neighbor.average_temperature, 0.18)
			p.average_moisture = lerp(p.average_moisture, neighbor.average_moisture, 0.18)
			p.average_height = lerp(p.average_height, neighbor.average_height, 0.12)
			p.rainfall = lerp(p.rainfall, neighbor.rainfall, 0.16)
			p.wind_strength = lerp(p.wind_strength, neighbor.wind_strength, 0.16)
			p.tectonic_activity = lerp(p.tectonic_activity, neighbor.tectonic_activity, 0.08)
			p.wind_direction = (p.wind_direction + neighbor.wind_direction).normalized()

	d.climate = p
	d.is_ocean = d.climate.average_height <= -0.42 or continent < -0.15
	d.terrain = TerrainGenerator.choose_region_terrain(d.climate, d.is_ocean)

	_generate_resources(d)

	if graph != null:
		graph.set_deca(coord, d)

	return d

static func _generate_resources(d: DecaChunkData) -> void:
	if d.is_ocean:
		d.resources = {
			"fish": 180,
			"salt": 70
		}
		return

	var h := d.climate.average_height
	var rain := d.climate.rainfall
	var temp := d.climate.average_temperature

	match d.terrain:
		BiomeData.Biome.HIGH_MOUNTAIN:
			d.resources = {
				"stone": 260,
				"iron": 90,
				"snow": 20
			}
		BiomeData.Biome.MOUNTAIN:
			d.resources = {
				"stone": 220,
				"iron": 60
			}
		BiomeData.Biome.SWAMP:
			d.resources = {
				"food": 80,
				"wood": 90,
				"herbs": 120
			}
		BiomeData.Biome.DESERT:
			d.resources = {
				"stone": 120,
				"salt": 80,
				"food": 20
			}
		BiomeData.Biome.SAVANNA:
			d.resources = {
				"food": 120,
				"wood": 40
			}
		BiomeData.Biome.TAIGA:
			d.resources = {
				"wood": 180,
				"food": 60,
				"fur": 90
			}
		BiomeData.Biome.SNOW:
			d.resources = {
				"fur": 120,
				"food": 30,
				"stone": 40
			}
		BiomeData.Biome.DENSE_FOREST:
			d.resources = {
				"wood": 260,
				"food": 90,
				"herbs": 60
			}
		BiomeData.Biome.FOREST:
			d.resources = {
				"wood": 200,
				"food": 80,
				"stone": 40
			}
		BiomeData.Biome.STEPPE:
			d.resources = {
				"food": 110,
				"wood": 30
			}
		_:
			if rain > 0.65 and temp > -0.2:
				d.resources = {
					"food": 120,
					"wood": 120
				}
			elif h > 0.25:
				d.resources = {
					"stone": 90,
					"food": 60
				}
			else:
				d.resources = {
					"food": 100,
					"wood": 50
				}