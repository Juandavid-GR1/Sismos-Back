import math


class SismoComparison:

    @staticmethod
    def tiene_cambios(
        sismo,
        magnitude,
        depth,
        epicenter_x,
        epicenter_y
    ) -> bool:

        return not (
            math.isclose(
                sismo.magnitude,
                magnitude,
                abs_tol=1e-1
            )
            and
            math.isclose(
                sismo.depth,
                depth,
                abs_tol=1e-1
            )
            and
            math.isclose(
                sismo.epicenter_x,
                epicenter_x,
                abs_tol=1e-1
            )
            and
            math.isclose(
                sismo.epicenter_y,
                epicenter_y,
                abs_tol=1e-1
            )
        )