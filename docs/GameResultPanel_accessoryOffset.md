# GameResultPanel accessoryOffset 변경 계획

## 계산 방식

```
ratio = GameResultPanel[BlueSlushy] / TownMainPanel[BlueSlushy]
      = -0.3 / -0.05 = 6.0

GameResultPanel[cookie] = TownMainPanel[cookie] × 6.0
```

## 전/후 값

| 쿠키 | TownMainPanel (현재) | GameResultPanel 현재 | GameResultPanel 목표 |
|------|:---:|:---:|:---:|
| CH_FruitPunch | -0.27 | -0.3 | -1.62 |
| CH_RedVelvet | -0.1 | -0.3 | -0.6 |
| CH_DarkChoco | -0.2 | -0.3 | -1.2 |
| CH_BaconRoll | 0 | -0.3 | 0 |
| CH_BlackPudding | 0 | -0.3 | 0 |
| CH_BlueberryPie | -0.18 | -0.3 | -1.08 |
| CH_BlueSlushy | -0.05 | -0.3 | **-0.3** ← 기준 |
| CH_BrieCheese | 0 | -0.3 | 0 |
| CH_Camembert | -0.15 | -0.3 | -0.9 |
| CH_Cherry | -0.13 | -0.3 | -0.78 |
| CH_ChiliPepper | -0.1 | -0.3 | -0.6 |
| CH_Espresso | -0.18 | -0.3 | -1.08 |
| CH_GingerBrave | -0.15 | -0.3 | -0.9 |
| CH_IcePop | -0.25 | -0.3 | -1.5 |
| CH_Jerky | 0 | -0.3 | 0 |
| CH_Latte | -0.08 | -0.3 | -0.48 |
| CH_Madeleine | -0.2 | -0.3 | -1.2 |
| CH_MelonSoda | -0.05 | -0.3 | -0.3 |
| CH_Peach | -0.18 | -0.3 | -1.08 |
| CH_Peppermint | -0.1 | -0.3 | -0.6 |
| CH_Rye | 0 | -0.3 | 0 |
| CH_StrawberryCrepe | -0.1 | -0.3 | -0.6 |
| CH_StringCheese | -0.01 | -0.3 | -0.06 |
| CH_TigerLily | -0.18 | -0.3 | -1.08 |

## 비고

- TownMainPanel에서 0인 쿠키 5종(BaconRoll, BlackPudding, BrieCheese, Jerky, Rye)은 비율 특성상 목표값도 0
- 별도 조정이 필요하면 수동으로 지정 필요
