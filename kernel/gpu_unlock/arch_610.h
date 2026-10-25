/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GPU_UNLOCK_ARCH_610_H
#define GPU_UNLOCK_ARCH_610_H

#ifdef __KERNEL__
#include <linux/types.h>
#else
#include <stdbool.h>
#endif

enum gpu_unlock_booter_arch {
	GU_BOOTER_GA10X = 0,
	GU_BOOTER_AD10X = 1,
};

#define GU_AD102_RTX_4090 0x2684u
/* Exact experimental AD103 canary; other Ada PCI IDs are not admitted. */
#define GU_AD103_RTX_4070_TI_SUPER 0x2705u
/* Exact experimental AD106 target, untested on silicon. */
#define GU_AD106_RTX_4060_TI_16GB 0x2805u

/* Exact experimental AD107M target; owner evidence is limited to one laptop. */
#define GU_AD107_RTX_4060_LAPTOP 0x28a0u
#define GU_AD107_SUBVENDOR 0x1d05u
#define GU_AD107_SUBDEVICE 0x1274u
#define GU_AD107_REVISION 0xa1u
#define GU_AD107_PMC_BOOT_0 0x197000a1u

/* RTX 4090 D uses the AD102 firmware path; gated as experimental. */
#define GU_AD102_RTX_4090_D 0x2685u

/* Asset selection and permission/readout checks must use the same family. */
static inline bool gpu_unlock_uses_ad102(unsigned short device)
{
	return device == GU_AD102_RTX_4090 ||
	       device == GU_AD102_RTX_4090_D ||
	       device == GU_AD103_RTX_4070_TI_SUPER ||
	       device == GU_AD106_RTX_4060_TI_16GB ||
	       device == GU_AD107_RTX_4060_LAPTOP;
}

#endif
