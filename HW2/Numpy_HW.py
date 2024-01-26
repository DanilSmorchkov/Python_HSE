import numpy as np
import typing as tp

###################
# Task 1-2       ##
###################


class Solution:
    """
    Класс для хранения решения СЛАУ методом Гаусса и дополнительной информации
    о решении
    """
    def __init__(self, single_flag: bool, freedom_degrees: int,
                 free_variables: np.ndarray | None, B: np.ndarray,
                 FSR: np.ndarray | None):
        self._single_flag = single_flag
        self._freedom_degrees = freedom_degrees
        self._free_variables = free_variables
        self._B = B
        self._FSR = FSR

    def is_single(self) -> bool:
        """
        Функция возвращает True, если решение единственно и False, в противном
        случае
        :return: bool в зависимости от количества решений (одно - True,
        бесконечно много - False)
        """
        return self._single_flag

    def freedom_degrees(self) -> int:
        """
        Возвращает число степеней свободы решения (0, если решение одно)
        :return: Число степеней свободы (Число свободных неизвестных)
        """
        return self._freedom_degrees

    def solutions(self) -> tp.Callable:
        """
        Функция, возвращающая функцию
        :return: callable объект любого класса, принимающий вектор длиной,
        равной числу степеней свободы решения и возвращающий решение,
        полученное применением переданных значений в качестве коэффициентов
        в формуле решения уравнения
        """
        if not np.any(self._free_variables):
            return lambda coeffs: self._B
        else:
            return self.__many_solutions

    def __many_solutions(self, coeffs: np.ndarray) -> np.ndarray:
        """
        Вспомогательная функция для реализации конкретного решения из ФСР
        :param coeffs: Коэффициенты свободных неизвестных (коэффициенты ФСР)
        :return: Вектор из ФСР, записанный в виде вектора np.ndarray
        """
        solutions = np.zeros(self._free_variables.shape[0])
        diff_solution = self._B - self._FSR @ coeffs
        solutions[np.where(self._free_variables == 0)[0]] = (diff_solution
                                                             .flatten())
        solutions[np.where(self._free_variables == 1)[0]] = coeffs
        return solutions


def gauss_solver(A_B: np.ndarray) -> None | Solution:
    """
    Функция решает систему линейных уравнений
    :param A_B: Матрица СЛАУ
    :return: возвращает None в случае отсутствия решения и объект класса
    Solution в случае, если решение есть.
    """
    n, m = A_B.shape[0], A_B.shape[1]
    row = 0
    col = 0
    # Массив для определения свободных переменных
    free_variable_array = np.ones(m - 1)
    # Идем по минимальной размерности матрицы (больше не пройдем)
    for i in range(min(n, m - 1)):
        # Вычисляем индекс максимального элемента в столбце
        index_max_elem = row + np.argmax(np.abs(A_B[row:, col]))
        # Переставляем строчку с максимальным элементом и нынешнюю строчку
        A_B[[row, index_max_elem], :] = A_B[[index_max_elem, row], :]
        # Проверка, что макс. значение не ноль
        # (для машинной точности: >= 10**(-10))
        if (np.abs(max_value := A_B[row, col])) >= 10**(-10):
            A_B[row, :] = A_B[row, :] / max_value
            # Прямой и обратный ход Гаусса
            for change_index in range(n):
                if change_index != row:
                    A_B[change_index, col:] -= (A_B[change_index, col] *
                                                A_B[row, col:])
            # Переменная с номером col не свободная (зависимая)
            free_variable_array[col] = 0
            #  Обновляем номер строки и столбца
            row += 1
            col += 1
        else:
            # В столбце только нули, смотрим следующий столбец
            # в следующей итерации
            col += 1
            continue
    # Нет решений
    if np.any(np.where(np.abs(A_B[row:, -1]) >= 10**(-15))[0]):
        return None
    # Решение одно
    elif np.sum(free_variable_array) == m - 1:
        return Solution(single_flag=True, freedom_degrees=0,
                        free_variables=None, B=A_B[:, -1], FSR=None)
    # Бесконечно решений
    else:
        return Solution(single_flag=False,
                        freedom_degrees=np.sum(free_variable_array),
                        free_variables=free_variable_array, B=A_B[:, -1],
                        FSR=A_B[:, np.where(free_variable_array == 1)[0]])


def task_1_2():
    n = 20
    m = 20
    np.random.seed(42)
    a = np.random.uniform(low=1, high=50, size=(n, m))
    # a = np.array([[1, 1, -1, -2], [2, 1, -1, 1], [-1, 1, -3, 1]])
    # a = np.array([[-1, 2, 1, -4, 3], [2, -1, -3, 1, -1], [3, 2, -1, -2, -5]],
    # dtype=np.float64)
    b = np.random.uniform(low=1, high=50, size=(n, 1))
    # b = np.array([0, -2, 4]).reshape((3, 1))
    # b = np.array([1, -4, 1], dtype=np.float64).reshape((3, 1))
    a_b = np.concatenate((a, b), axis=1)
    solution = gauss_solver(a_b)
    single = solution.is_single()
    freedom_degrees = solution.freedom_degrees()
    get_solution = solution.solutions()
    solution = get_solution(5 + np.arange(freedom_degrees))
    b_mult = np.dot(a, solution)
    print(freedom_degrees)
    print(single)
    print(solution)
    print()
    print(b_mult.reshape((n, 1)) - b)


###################
# Task 3         ##
###################


def gcd(n_m: np.ndarray) -> np.ndarray:
    """
    Функция вычисляет НОД для каждой строки для вектора (n, 2) с помощью
    алгоритма Евклида
    :param n_m: np.ndarray с парами чисел, для которых требуется найти НОД
    :return: np.ndarray размером (n, 1), в котором хранятся НОД для всех
    пар в начальном массиве
    """
    answer = n_m.copy()
    while True:
        # Маска для строк, у которых во втором столбце не ноль
        mask = np.where(answer[:, 1] != 0)[0]
        # Когда везде нули во втором столбце, мы нашли все НОД
        if not np.any(answer[:, 1]):
            return answer[:, 0]
        answer[mask] = np.concatenate(
            (answer[mask, 1].reshape((mask.shape[0], 1)),
             (answer[mask, 0] % answer[mask, 1]).reshape((mask.shape[0], 1))),
            axis=1)


def task_3():
    n = 100
    n_m = np.random.randint(low=2, high=1000, size=(n, 2))
    ans = gcd(n_m)
    print(n_m.T)
    print(ans)


###################
# Task 4         ##
###################


def broadcaster(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Функция складывает два np.ndarray, реализуя обобщенный broadcast.
    Отличие обобщенного от классического в том, что если по какому-то измерению
    число меньшее число элементов делит нацело большее, то мы его применяем
    циклически.
    :param a: Первый массив np.ndarray
    :param b: Второй массив np.ndarray
    :return: Сумма a и b с обобщенным broadcast
    """
    num_of_dims = np.max((len(a.shape), len(b.shape)))
    #  Запоминаем начальные размеры
    a_shape = np.copy(a.shape).astype(np.int16)
    b_shape = np.copy(b.shape).astype(np.int16)
    if len(a_shape) > len(b_shape):
        b_shape = np.concatenate((b_shape,
                                  np.ones(len(a_shape) - len(b_shape),
                                          dtype=np.int16)), dtype=np.int16)
        b = b.reshape(b_shape)
    else:
        a_shape = np.concatenate((a_shape,
                                  np.ones(len(b_shape) - len(a_shape),
                                          dtype=np.int16)), dtype=np.int16)
        a = a.reshape(a_shape)
    # Идем по максимальной размерности и множим минимальный массив
    # для данной размерности
    for dim in range(num_of_dims):
        if a_shape[dim] < b_shape[dim] and b_shape[dim] % a_shape[dim] == 0:
            list_ = np.ones(num_of_dims, dtype=np.int16)
            list_[dim] = b_shape[dim] // a_shape[dim]
            a = np.tile(a, list_)
        elif a_shape[dim] > b_shape[dim] and a_shape[dim] % b_shape[dim] == 0:
            list_ = np.ones(num_of_dims, dtype=np.int16)
            list_[dim] = a_shape[dim] // b_shape[dim]
            b = np.tile(b, list_)
    return a + b


def task_4():
    a = np.random.randint(low=1, high=10, size=(10, 2, 4))
    b = np.random.randint(low=1, high=10, size=(5, 6, 1, 6))
    c = broadcaster(a, b)
    print(c)


def main():
    task_1_2()
    task_3()
    task_4()


if __name__ == '__main__':
    main()
