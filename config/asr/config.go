package config

import "github.com/ilyakaznacheev/cleanenv"

type Config struct {
	Port int `env:"PORT"`
}

func MustLoad() *Config {
	var cfg Config
	if err := cleanenv.ReadEnv(&cfg); err != nil {
		panic("failed to read environment variables: " + err.Error())
	}

	return &cfg
}
