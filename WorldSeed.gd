extends Node

var seed:=0

var continent_noise:FastNoiseLite

var climate_noise:FastNoiseLite

var height_noise:FastNoiseLite

var moisture_noise:FastNoiseLite

func _ready():

	if seed==0:

		set_seed(randi())

func set_seed(new_seed:int):

	seed=new_seed

	randomize()

	continent_noise=FastNoiseLite.new()
	continent_noise.seed=seed
	continent_noise.frequency=0.0007

	climate_noise=FastNoiseLite.new()
	climate_noise.seed=seed+1000
	climate_noise.frequency=0.002

	height_noise=FastNoiseLite.new()
	height_noise.seed=seed+2000
	height_noise.frequency=0.01

	moisture_noise=FastNoiseLite.new()
	moisture_noise.seed=seed+3000
	moisture_noise.frequency=0.015

func continent(pos:Vector2)->float:

	return continent_noise.get_noise_2d(pos.x,pos.y)

func climate(pos:Vector2)->float:

	return climate_noise.get_noise_2d(pos.x,pos.y)

func height(pos:Vector2)->float:

	return height_noise.get_noise_2d(pos.x,pos.y)

func moisture(pos:Vector2)->float:

	return moisture_noise.get_noise_2d(pos.x,pos.y)