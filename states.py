from aiogram.fsm.state import State, StatesGroup


class AddBook(StatesGroup):
    title = State()
    author = State()
    genre = State()
    book_type = State()
    file = State()
    cover = State()
    description = State()
    price = State()
    confirm = State()


class SearchBook(StatesGroup):
    query = State()


class MakeOrder(StatesGroup):
    title = State()
    details = State()


class RateBook(StatesGroup):
    book_id = State()
    rating = State()
    comment = State()


class SetOrderPrice(StatesGroup):
    order_id = State()
    price = State()
