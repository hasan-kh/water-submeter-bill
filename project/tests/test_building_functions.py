from django.test import TestCase

from building.functions import get_price_over_14_m3, round_price


class TestFunctions(TestCase):

    def test_get_price_over_14_m3(self) -> None:
        to_test = [

            [1, 0.001*2824],
            [356, 0.356*2824],
            [499, 0.499*2824],
            [500, 0.5*2824],

            [10001, (10.001* 5630) - 21035],
            [12568, (12.568* 5630) - 21035],
            [14000, (14.000* 5630) - 21035],

            [43889, (43.889 * 100866) - 3178333],
            [50000, (50.000 * 100866) - 3178333],
            [54201, (54.201 * 100866) - 3178333],

            [56001, (56.001 * 168110) - 6943997],
            [73452, (73.452 * 168110) - 6943997],
            [102480, (102.480 * 168110) - 6943997],
        ]

        for i in to_test:
            with self.subTest(i=i):
                self.assertEqual(get_price_over_14_m3(i[0]), i[1])
    
    def test_round_price(self) -> None:
        to_test = [
            [0, 0],

            [1, 100],
            [99, 100],
            [100, 100],

            [153, 200],
            [978, 1000],

            [8649, 8600],
            [8650, 8700],
            [8651, 8700],
            [9980, 10000],
            [14500, 14500],
            [14560, 14600],

            [112120, 112100],
            [260800, 260800],
        ]

        for i in to_test:
            with self.subTest(i=i):
                self.assertEqual(round_price(i[0]), i[1])
