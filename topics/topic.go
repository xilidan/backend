package topics

type Topic struct {
	prefix string
	name   string
}

func New(prefix, name string) Topic {
	return Topic{
		prefix: prefix,
		name:   name,
	}
}

func (t Topic) FullName() string {
	if t.prefix == "" {
		return t.name
	}
	return t.prefix + "." + t.name
}

func (t Topic) Name() string {
	if t.prefix == "" {
		return t.name
	}
	return t.prefix + "." + t.name
}
