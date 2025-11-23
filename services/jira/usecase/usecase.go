package usecase

type usecase struct {

}

type Usecase interface {

}

func New() Usecase {
	return &usecase{}
}
