// SPDX-License-Identifier: GPL-2.0-only
/* Observer only. Called with the normal voter lock; never changes a vote, a
 * list or an outgoing command. Only a completed ordinary commit can publish.
 */
static int g0q_bcm_index(const char *name)
{
	if (!strcmp(name, "SH1"))
		return 0;
	if (!strcmp(name, "CN0"))
		return 1;
	return -1;
}

static void g0q_trace_queued(struct bcm_voter *voter, struct tcs_cmd *cmds,
			     int *counts, struct g0q_bcm_confirmation scratch[2])
{
	struct qcom_icc_bcm *bcm;

	if (!voter->g0q_primary)
		return;
	list_for_each_entry(bcm, &voter->commit_list, list) {
		struct g0q_bcm_confirmation *row;
		int index = g0q_bcm_index(bcm->name);
		unsigned int off = 0;
		unsigned int occurrences = 0;

		if (index < 0)
			continue;
		row = &scratch[index];
		row->seen = true;
		/* Invalidate old confirmation on every attempted update. */
		voter->g0q_applied[index].known = false;
		for (int batch = 0; batch < MAX_VCD && counts[batch]; batch++) {
			bool found = false;
			for (int n = 0; n < counts[batch]; n++, off++) {
				struct tcs_cmd *cmd = &cmds[off];
				if (cmd->addr == bcm->addr) {
					struct tcs_cmd wanted;
					occurrences++;
					tcs_cmd_gen(&wanted, bcm->vote_x[QCOM_ICC_BUCKET_AMC],
						    bcm->vote_y[QCOM_ICC_BUCKET_AMC], bcm->addr, false, false);
					found = ((cmd->data ^ wanted.data) & ~BCM_TCS_CMD_COMMIT_MASK) == 0;
				}
				if (cmd->data & BCM_TCS_CMD_COMMIT_MASK) {
					if (found && cmd->wait)
						row->known = true;
					found = false;
				}
			}
		}
		row->known &= occurrences == 1;
		memcpy(row->x, bcm->vote_x, sizeof(row->x));
		memcpy(row->y, bcm->vote_y, sizeof(row->y));
	}
}

static void g0q_trace_finish(struct bcm_voter *voter,
			     const struct g0q_bcm_confirmation scratch[2], int rc)
{
	if (!voter->g0q_primary)
		return;
	for (int i = 0; i < 2; i++) {
		if (rc)
			voter->g0q_applied[i].known = false;
		else if (scratch[i].seen)
			voter->g0q_applied[i] = scratch[i];
	}
}

int g0q_bcm_confirm_usb(struct g0q_usb_report *report)
{
	struct bcm_voter *voter;
	int rc = g0q_rpmh_remaining();

	if (rc)
		return g0q_usb_fail(report, G0Q_USB_RUN_STATE, (u32)rc, rc);
	if (!mutex_trylock(&bcm_voter_lock))
		return g0q_usb_fail(report, G0Q_BCM_GLOBAL_LOCK, 0, -EBUSY);
	rc = g0q_usb_fail(report, G0Q_BCM_VOTER, 0, -ENODEV);
	list_for_each_entry(voter, &bcm_voters, voter_node) {
		if (!voter->g0q_primary)
			continue;
		if (!mutex_trylock(&voter->lock)) {
			rc = g0q_usb_fail(report, G0Q_BCM_LOCK, 0, -EBUSY);
			break;
		}
		if (!list_empty(&voter->commit_list)) {
			rc = g0q_usb_fail(report, G0Q_BCM_PENDING, 1, -EBUSY);
			goto unlock;
		}
		for (int i = 0; i < 2; i++) {
			const struct g0q_bcm_confirmation *row = &voter->g0q_applied[i];
			if (!row->known) {
				rc = g0q_usb_fail(report, G0Q_BCM_UNKNOWN, i, -EBUSY);
				goto unlock;
			}
			if (row->y[QCOM_ICC_BUCKET_AMC] != 1 ||
			    row->y[QCOM_ICC_BUCKET_WAKE] != 1 || row->y[QCOM_ICC_BUCKET_SLEEP] != 1 ||
			    row->x[QCOM_ICC_BUCKET_AMC] != i || row->x[QCOM_ICC_BUCKET_WAKE] != i ||
			    row->x[QCOM_ICC_BUCKET_SLEEP] != 0) {
				/* Two bits per protected scalar: 0, 1, 2, or >=3. */
				u32 detail = i << 16;
				for (int b = 0; b < QCOM_ICC_NUM_BUCKETS; b++) {
					detail |= (u32)(row->x[b] < 3 ? row->x[b] : 3) << (b * 4);
					detail |= (u32)(row->y[b] < 3 ? row->y[b] : 3) << (b * 4 + 2);
				}
				rc = g0q_usb_fail(report, G0Q_BCM_VALUES, detail, -EBUSY);
				goto unlock;
			}
		}
		rc = g0q_rpmh_remaining();
		g0q_usb_fail(report, rc ? G0Q_USB_RUN_STATE : G0Q_USB_OK, (u32)rc, rc);
unlock:
		mutex_unlock(&voter->lock);
		break;
	}
	mutex_unlock(&bcm_voter_lock);
	return rc;
}
EXPORT_SYMBOL_GPL(g0q_bcm_confirm_usb);
